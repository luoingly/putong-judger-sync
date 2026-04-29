import logging
from pathlib import Path

import yaml

from judger.models import ProblemType

from .models import Problem, ProblemConstraints, TestCaseData

logger = logging.getLogger(__name__)


class ProblemLoader:
    @staticmethod
    def load(problem_dir: Path) -> Problem:
        if not problem_dir.is_dir():
            raise FileNotFoundError(f"Problem directory not found: {problem_dir}")

        problem_id = problem_dir.name

        yaml_path = problem_dir / "problem.yaml"
        if not yaml_path.exists():
            raise FileNotFoundError(f"problem.yaml not found in {problem_dir}")

        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        title = data.get("title", problem_id)
        source = data.get("source", "")

        raw_constraints = data.get("constraints", {})
        problem_type_str = raw_constraints.get("problemType", "traditional")
        problem_type = _parse_problem_type(problem_type_str)

        constraints = ProblemConstraints(
            timeLimit=raw_constraints.get("timeLimit", 1000),
            memoryLimit=raw_constraints.get("memoryLimit", 32768),
            problemType=problem_type,
        )

        description_path = problem_dir / "description.md"

        addition_code_path: Path | None = None
        if problem_type in (ProblemType.Interaction, ProblemType.SpecialJudge):
            addition_code_path = problem_dir / "addition.cpp"
            if not addition_code_path.exists():
                raise FileNotFoundError(
                    f"addition.cpp required for {problem_type.name} "
                    f"problems but not found in {problem_dir}"
                )

        testcases = _scan_testcases(problem_dir / "tests")

        problem = Problem(
            id=problem_id,
            title=title,
            source=source,
            constraints=constraints,
            testcases=testcases,
            problem_dir=problem_dir,
            description_path=description_path if description_path.exists() else None,
            addition_code_path=addition_code_path,
        )

        logger.info("Loaded problem '%s' with %d testcases", problem_id, len(testcases))
        return problem


def _parse_problem_type(s: str) -> ProblemType:
    mapping = {
        "traditional": ProblemType.Traditional,
        "interaction": ProblemType.Interaction,
        "special-judge": ProblemType.SpecialJudge,
    }
    if s not in mapping:
        raise ValueError(f"Unknown problem type: {s}. Must be one of {list(mapping.keys())}")
    return mapping[s]


def _scan_testcases(tests_dir: Path) -> list[TestCaseData]:
    if not tests_dir.is_dir():
        logger.warning("Tests directory not found: %s", tests_dir)
        return []

    testcases = []
    for in_file in sorted(tests_dir.glob("*.in")):
        out_file = in_file.with_suffix(".out")
        if not out_file.exists():
            logger.warning("No matching .out file for %s, skipping", in_file.name)
            continue
        uuid = in_file.stem
        testcases.append(
            TestCaseData(
                uuid=uuid,
                input_path=in_file,
                output_path=out_file,
            )
        )

    return testcases
