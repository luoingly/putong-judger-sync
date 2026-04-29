import logging
from pathlib import Path

from .loader import ProblemLoader
from .models import Problem

logger = logging.getLogger(__name__)


class ProblemRegistry:
    def __init__(self, problems_dir: Path):
        self._problems: dict[str, Problem] = {}
        self._load_all(problems_dir)

    def _load_all(self, problems_dir: Path) -> None:
        if not problems_dir.is_dir():
            raise FileNotFoundError(f"Problems directory not found: {problems_dir}")

        for subdir in sorted(problems_dir.iterdir()):
            if subdir.is_dir() and (subdir / "problem.yaml").exists():
                try:
                    problem = ProblemLoader.load(subdir)
                    self._problems[problem.id] = problem
                except Exception:
                    logger.exception("Failed to load problem from %s", subdir)

        logger.info("Loaded %d problems from %s", len(self._problems), problems_dir)

    def get(self, problem_id: str) -> Problem:
        if problem_id not in self._problems:
            available = list(self._problems.keys())
            raise KeyError(f"Problem '{problem_id}' not found. Available: {available}")
        return self._problems[problem_id]

    def list_all(self) -> list[Problem]:
        return list(self._problems.values())

    @property
    def ids(self) -> list[str]:
        return list(self._problems.keys())
