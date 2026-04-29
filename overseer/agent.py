import logging
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from overseer.problems.models import Problem
from overseer.provider import AIResponse, Message, Usage
from overseer.tools.definitions import ALL_TOOLS
from overseer.tools.executor import ToolExecutor

logger = logging.getLogger(__name__)


class AgentStatus(StrEnum):
    Completed = "completed"
    Failed = "failed"
    Timeout = "timeout"


@dataclass
class AgentResult:
    status: AgentStatus
    code: str | None = None
    language: str | None = None
    token_usage: Usage | None = None
    turn_count: int = 0
    conversation: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


SYSTEM_PROMPT = """\
你是一名竞赛选手，正在解答算法题目。\
你可以使用工具来阅读题目、运行代码和提交解答。
"""


def _extract_code(text: str | None, language_hint: str | None = None) -> str | None:
    if not text:
        return None

    if language_hint:
        pattern = rf"```{language_hint}\s*\n(.*?)```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()

    pattern = r"```(?:\w+)?\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()

    return None


def _message_to_record(msg: Message) -> dict[str, Any]:
    record: dict[str, Any] = {"role": msg.role}
    if msg.content is not None:
        record["content"] = msg.content
    if msg.reasoning_content is not None:
        record["reasoning_content"] = msg.reasoning_content
    return record


def _response_to_record(resp: AIResponse, model: str | None = None) -> dict[str, Any]:
    record: dict[str, Any] = {"role": "assistant", "model": model}
    if resp.content:
        record["content"] = resp.content
    if resp.reasoning_content:
        record["reasoning_content"] = resp.reasoning_content
    if resp.tool_calls:
        record["tool_calls"] = [
            {
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in resp.tool_calls
        ]
    if resp.usage:
        record["usage"] = {
            "prompt_tokens": resp.usage.prompt_tokens,
            "completion_tokens": resp.usage.completion_tokens,
            "total_tokens": resp.usage.total_tokens,
            "prompt_tokens_details": resp.usage.prompt_tokens_details,
            "completion_tokens_details": resp.usage.completion_tokens_details,
        }
    return record


class ToolAgent:
    def __init__(
        self,
        language_name: str,
        max_turns: int = 10,
        tool_executor: ToolExecutor | None = None,
    ):
        self.language_name = language_name
        self.max_turns = max_turns
        self.tool_executor = tool_executor

    async def solve(
        self,
        problem: Problem,
        provider: Any,  # AIProvider
    ) -> AgentResult:
        if not self.tool_executor:
            return AgentResult(
                status=AgentStatus.Failed,
                error="ToolAgent requires a tool_executor",
                conversation=[],
            )

        system_prompt = SYSTEM_PROMPT.format(language=self.language_name)
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=f"请开始，阅读题目并解答。"),
        ]
        conversation = [_message_to_record(m) for m in messages]

        total_usage = Usage()
        last_code: str | None = None
        response: AIResponse | None = None

        for turn in range(self.max_turns):
            try:
                response = await provider.complete(messages, tools=ALL_TOOLS)
            except Exception as e:
                logger.exception("ToolAgent: provider call failed at turn %d", turn + 1)
                return AgentResult(
                    status=AgentStatus.Failed,
                    code=last_code,
                    language=self.language_name,
                    token_usage=total_usage,
                    turn_count=turn + 1,
                    conversation=conversation,
                    error=str(e),
                )

            if response.usage:
                total_usage = total_usage + response.usage

            conversation.append(_response_to_record(response, provider.config.name))

            assistant_msg = Message(
                role="assistant",
                content=response.content,
                tool_calls=response.tool_calls,
                reasoning_content=response.reasoning_content,
            )
            messages.append(assistant_msg)

            if not response.tool_calls:
                logger.debug("ToolAgent: no tool calls at turn %d, finishing", turn + 1)
                break

            for tc in response.tool_calls:
                args = tc.function.arguments
                if not isinstance(args, dict):
                    args = {}

                logger.info("ToolAgent: executing tool '%s' with args: %s", tc.function.name, args)
                result_str = await self.tool_executor.execute(tc.function.name, args)

                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "tool_name": tc.function.name,
                        "content": result_str,
                    }
                )

                tool_msg = Message(
                    role="tool",
                    content=result_str,
                    tool_call_id=tc.id,
                )
                messages.append(tool_msg)

                if tc.function.name == "submit_code" and "code" in args:
                    last_code = args["code"]

        final_code = last_code
        if not final_code and response and response.content:
            final_code = _extract_code(response.content, self.language_name) or _extract_code(
                response.content
            )

        turn_count = len([m for m in conversation if m.get("role") == "assistant"])

        return AgentResult(
            status=AgentStatus.Completed if final_code else AgentStatus.Failed,
            code=final_code,
            language=self.language_name,
            token_usage=total_usage,
            turn_count=turn_count,
            conversation=conversation,
        )
