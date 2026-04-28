from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from judger.api import app, get_client
from judger.models import JudgeStatus, Language, ProblemType, SubmissionResult, TestcaseResult


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def test_client(mock_client):
    app.dependency_overrides[get_client] = lambda: mock_client
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_root_endpoint(test_client):
    response = test_client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "Putong OJ Judger API"


def test_health_endpoint(test_client):
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_judge_accepted(test_client, mock_client):
    mock_judger = MagicMock()
    mock_judger.get_result = AsyncMock(
        return_value=SubmissionResult(
            sid=1,
            time=10,
            memory=256,
            testcases=[TestcaseResult(uuid="t1", time=10, memory=256, judge=JudgeStatus.Accepted)],
            judge=JudgeStatus.Accepted,
            error=""
        )
    )

    with patch('judger.api.Judger', return_value=mock_judger):
        response = test_client.post(
            "/judge",
            json={
                "sid": 1,
                "timeLimit": 1000,
                "memoryLimit": 32768,
                "testcases": [{"uuid": "t1", "input": {"content": "1"}, "output": {"content": "1"}}],
                "language": Language.C,
                "code": "int main() { return 0; }"
            }
        )

    assert response.status_code == 200
    data = response.json()
    assert data["judgeResult"] == "Accepted"
    assert data["testcases"][0]["judgeResult"] == "Accepted"
    assert "sid" not in data


def test_judge_invalid_language(test_client):
    response = test_client.post(
        "/judge",
        json={
            "sid": 1,
            "timeLimit": 1000,
            "memoryLimit": 32768,
            "testcases": [{"uuid": "t1", "input": {"content": "1"}, "output": {"content": "1"}}],
            "language": 999,
            "code": "print(1)"
        }
    )
    assert response.status_code == 422


def test_run_accepted(test_client, mock_client):
    from judger.models import SandboxResult, SandboxStatus

    call_count = [0]

    async def mock_run(cmds):
        call_count[0] += 1
        if call_count[0] == 1:
            return [SandboxResult(status=SandboxStatus.Accepted, exitStatus=0, fileIds={"Main": "id"})]
        return [SandboxResult(status=SandboxStatus.Accepted, exitStatus=0, time=10_000_000, files={"stdout": "42\n"})]

    mock_client.run_command = mock_run
    mock_client.delete_file = AsyncMock(return_value=True)

    response = test_client.post(
        "/run",
        json={"language": Language.C, "code": "int main() { printf(\"42\\n\"); }", "input": ""}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["compileStatus"] == "Success"
    assert data["runStatus"] == "Accepted"
    assert data["stdout"] == "42\n"


def test_run_compile_error(test_client, mock_client):
    from judger.models import SandboxResult, SandboxStatus

    mock_client.run_command = AsyncMock(
        return_value=[SandboxResult(status=SandboxStatus.NonzeroExitStatus, files={"stderr": "error"})]
    )

    response = test_client.post(
        "/run",
        json={"language": Language.C, "code": "invalid"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["compileStatus"] == "Failed"


def test_run_invalid_language(test_client):
    response = test_client.post(
        "/run",
        json={"language": 999, "code": "print(1)"}
    )
    assert response.status_code == 422
