import logging
from typing import Any

from judger.client import SandboxClient
from judger.judger import Judger
from judger.language import LanguageRegistry
from judger.models import (
    Collector,
    Language,
    MemoryFile,
    PreparedFile,
    SandboxCmd,
    SandboxStatus,
    Submission,
    Testcase,
)
from overseer.problems.models import Problem

logger = logging.getLogger(__name__)


class ToolExecutor:
    def __init__(
        self,
        problem: Problem,
        sandbox_client: SandboxClient,
        language: Language,
    ):
        self.problem = problem
        self.sandbox = sandbox_client
        self.language = language

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        handlers = {
            "read_problem": self._read_problem,
            "submit_code": self._submit_code,
            "run_code": self._run_code,
            "check_testcase": self._check_testcase,
        }
        handler = handlers.get(tool_name)
        if not handler:
            return f"Error: Unknown tool '{tool_name}'"
        try:
            return await handler(arguments)
        except Exception as e:
            logger.exception("Tool '%s' execution failed", tool_name)
            return f"Error executing {tool_name}: {e}"

    async def _read_problem(self, args: dict[str, Any]) -> str:
        statement = self.problem.read_statement()
        constraints = self.problem.constraints
        result = statement
        result += "\n\n## Constraints\n"
        result += f"- Time Limit: {constraints.timeLimit}ms\n"
        result += f"- Memory Limit: {constraints.memoryLimit}KB\n"
        result += f"- Problem Type: {constraints.problemType.name}\n"
        result += f"\n## Language: {self.language.name}\n"
        return result

    async def _submit_code(self, args: dict[str, Any]) -> str:
        code = args.get("code", "")
        if not code:
            return "Error: No code provided"

        submission = build_submission(self.problem, code, self.language)
        judger = Judger(client=self.sandbox, submission=submission)
        result = await judger.get_result()

        lines = [f"Result: {result.judge.name}"]
        if result.error:
            lines.append(f"Error: {result.error}")
        lines.append(f"Time: {result.time}ms | Memory: {result.memory}KB")
        lines.append("")
        for tc in result.testcases:
            status = _status_icon(tc.judge.name)
            lines.append(f"  {tc.uuid}: {status} {tc.judge.name} ({tc.time}ms, {tc.memory}KB)")
        return "\n".join(lines)

    async def _run_code(self, args: dict[str, Any]) -> str:
        code = args.get("code", "")
        input_data = args.get("input", "")
        if not code:
            return "Error: No code provided"

        lang_config = LanguageRegistry.get_config(self.language)
        constraints = self.problem.constraints
        compiled_id: str | None = None

        if lang_config.need_compile:
            compile_cmd = SandboxCmd(
                args=lang_config.compile_cmd,
                files=[MemoryFile(""), Collector("stdout"), Collector("stderr")],
                copyIn={lang_config.source_filename: MemoryFile(code)},
                copyOutCached=[lang_config.compiled_filename],
            )
            compile_result = (await self.sandbox.run_command([compile_cmd]))[0]
            if compile_result.status != SandboxStatus.Accepted:
                stderr = (compile_result.files or {}).get("stderr", "")
                return f"Compile Error:\n{stderr}"

            compiled_id = (compile_result.fileIds or {}).get(lang_config.compiled_filename)
            if not compiled_id:
                return "Compile Error: compiled file not found in sandbox response"
            run_copy_in = {lang_config.compiled_filename: PreparedFile(compiled_id)}
        else:
            run_copy_in = {lang_config.source_filename: MemoryFile(code)}

        timeLimit = 1_000_000 * constraints.timeLimit * lang_config.time_factor
        memoryLimit = 1024 * constraints.memoryLimit * lang_config.memory_factor

        run_cmd = SandboxCmd(
            args=lang_config.run_cmd,
            cpuLimit=timeLimit,
            clockLimit=timeLimit * 2,
            memoryLimit=memoryLimit,
            files=[MemoryFile(input_data), Collector("stdout"), Collector("stderr")],
            copyIn=run_copy_in,
        )
        run_result = (await self.sandbox.run_command([run_cmd]))[0]

        if compiled_id:
            try:
                await self.sandbox.delete_file(compiled_id)
            except Exception:
                logger.debug("Failed to delete compiled file %s", compiled_id)

        files = run_result.files or {}
        stdout = files.get("stdout", "")
        stderr = files.get("stderr", "")
        lines = [
            f"Status: {run_result.status.value}",
            f"Time: {run_result.time // 1_000_000}ms | Memory: {run_result.memory // 1024}KB",
        ]
        if stdout:
            lines.append(f"\n--- stdout ---\n{stdout}")
        if stderr:
            lines.append(f"\n--- stderr ---\n{stderr}")
        return "\n".join(lines)

    async def _check_testcase(self, args: dict[str, Any]) -> str:
        code = args.get("code", "")
        testcase_name = args.get("testcase_name", "")
        if not code:
            return "Error: No code provided"
        if not testcase_name:
            return "Error: No testcase name provided"

        try:
            input_data = self.problem.read_test_input(testcase_name)
            expected = self.problem.read_test_output(testcase_name)
        except ValueError as e:
            return f"Error: {e}"

        run_result = await self._run_code({"code": code, "input": input_data})

        return f"{run_result}\n\n--- Expected Output ---\n{expected}"


def build_submission(problem: Problem, code: str, language: Language) -> Submission:
    testcases = []
    for tc in problem.testcases:
        testcases.append(
            Testcase(
                uuid=tc.uuid,
                input=MemoryFile(tc.read_input()),
                output=MemoryFile(tc.read_output()),
            )
        )

    return Submission(
        sid=0,
        timeLimit=problem.constraints.timeLimit,
        memoryLimit=problem.constraints.memoryLimit,
        testcases=testcases,
        language=language,
        code=code,
        type=problem.constraints.problemType,
        additionCode=problem.read_addition_code() or "",
    )


def _status_icon(status_name: str) -> str:
    if status_name == "Accepted":
        return "✓"
    elif status_name == "Skipped":
        return "—"
    else:
        return "✗"
