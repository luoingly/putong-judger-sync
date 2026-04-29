import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from judger.models import SubmissionResult
from overseer.agent import AgentResult

logger = logging.getLogger(__name__)


class Recorder:
    def __init__(self, output_dir: Path | None = None):
        if output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path("data/records") / timestamp
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._summaries: list[dict[str, Any]] = []

    async def save(
        self,
        model_name: str,
        problem_id: str,
        language: str,
        agent_result: AgentResult,
        judge_result: SubmissionResult | None,
        elapsed_seconds: float,
    ) -> Path:
        record: dict[str, Any] = {
            "model": model_name,
            "problem": problem_id,
            "language": language,
            "status": agent_result.status.value if agent_result.status else None,
            "elapsed_seconds": round(elapsed_seconds, 2),
            "turn_count": agent_result.turn_count,
            "conversation": agent_result.conversation,
        }

        if agent_result.token_usage:
            usage = agent_result.token_usage
            record["token_usage"] = {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "prompt_tokens_details": usage.prompt_tokens_details,
                "completion_tokens_details": usage.completion_tokens_details,
            }

        if agent_result.error:
            record["error"] = agent_result.error

        if judge_result:
            record["judge_detail"] = {
                "status": judge_result.judge.name,
                "time": judge_result.time,
                "memory": judge_result.memory,
                "error": judge_result.error or None,
                "testcases": [
                    {
                        "uuid": tc.uuid,
                        "status": tc.judge.name,
                        "time": tc.time,
                        "memory": tc.memory,
                    }
                    for tc in judge_result.testcases
                ],
            }

        filename = f"{model_name}__{problem_id}.json"
        filepath = self.output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        logger.info("Record saved to %s", filepath)

        judge_status = record.get("judge_detail", {}).get("status") or (
            agent_result.status.value if agent_result.status else "unknown"
        )
        self._summaries.append(
            {
                "model": model_name,
                "problem": problem_id,
                "language": language,
                "status": judge_status,
                "turn_count": agent_result.turn_count,
                "token_usage": record.get("token_usage", {}).get("total_tokens", 0),
                "elapsed_seconds": round(elapsed_seconds, 2),
                "output_file": filename,
            }
        )

        return filepath

    def save_run_summary(self) -> Path:
        filepath = self.output_dir / "run.yaml"
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(
                {
                    "created_at": datetime.now().isoformat(),
                    "results": self._summaries,
                },
                f,
                default_flow_style=False,
                allow_unicode=True,
            )

        logger.info("Run summary saved to %s", filepath)
        return filepath
