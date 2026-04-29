from dataclasses import dataclass, field
from pathlib import Path

from judger.models import ProblemType


@dataclass
class ProblemConstraints:
    timeLimit: int  # ms
    memoryLimit: int  # KB
    problemType: ProblemType = ProblemType.Traditional

    def __post_init__(self):
        if not isinstance(self.problemType, ProblemType):
            self.problemType = ProblemType(self.problemType)


@dataclass
class TestCaseData:
    uuid: str
    input_path: Path
    output_path: Path

    def read_input(self) -> str:
        return self.input_path.read_text(encoding="utf-8")

    def read_output(self) -> str:
        return self.output_path.read_text(encoding="utf-8")


@dataclass
class Problem:
    id: str
    title: str
    constraints: ProblemConstraints = field(
        default_factory=lambda: ProblemConstraints(timeLimit=1000, memoryLimit=32768)
    )
    testcases: list[TestCaseData] = field(default_factory=list)
    problem_dir: Path | None = None
    description_path: Path | None = None
    addition_code_path: Path | None = None

    def read_description(self) -> str:
        if self.description_path and self.description_path.exists():
            return self.description_path.read_text(encoding="utf-8")
        return ""

    def read_addition_code(self) -> str:
        if self.addition_code_path and self.addition_code_path.exists():
            return self.addition_code_path.read_text(encoding="utf-8")
        return ""

    def read_test_input(self, uuid: str) -> str:
        for tc in self.testcases:
            if tc.uuid == uuid:
                return tc.read_input()
        raise ValueError(f"Testcase '{uuid}' not found")

    def read_test_output(self, uuid: str) -> str:
        for tc in self.testcases:
            if tc.uuid == uuid:
                return tc.read_output()
        raise ValueError(f"Testcase '{uuid}' not found")
