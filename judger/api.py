import logging
import os
import random
from contextlib import asynccontextmanager
from typing import Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field, model_validator

from .client import SandboxClient
from .config import DEFAULT_MEMORY_LIMIT, DEFAULT_TIME_LIMIT, LOGGER_NAME
from .judger import Judger
from .language import LanguageRegistry
from .models import (
    Collector,
    JudgeStatus,
    Language,
    MemoryFile,
    PreparedFile,
    ProblemType,
    SandboxCmd,
    SandboxStatus,
    Submission,
    SubmissionResult,
    Testcase,
    TestcaseResult,
)

logger = logging.getLogger(f"{LOGGER_NAME}.api")

# Status mappings
_JUDGE_STATUS_MAP = {
    JudgeStatus.Accepted: "Accepted",
    JudgeStatus.WrongAnswer: "Wrong Answer",
    JudgeStatus.PresentationError: "Presentation Error",
    JudgeStatus.TimeLimitExceeded: "Time Limit Exceeded",
    JudgeStatus.MemoryLimitExceeded: "Memory Limit Exceeded",
    JudgeStatus.OutputLimitExceeded: "Output Limit Exceeded",
    JudgeStatus.RuntimeError: "Runtime Error",
    JudgeStatus.CompileError: "Compile Error",
    JudgeStatus.SystemError: "System Error",
    JudgeStatus.Skipped: "Skipped",
}

_SANDBOX_STATUS_MAP = {
    SandboxStatus.Accepted: "Accepted",
    SandboxStatus.TimeLimitExceeded: "Time Limit Exceeded",
    SandboxStatus.MemoryLimitExceeded: "Memory Limit Exceeded",
    SandboxStatus.OutputLimitExceeded: "Output Limit Exceeded",
    SandboxStatus.NonzeroExitStatus: "Runtime Error",
    SandboxStatus.Signalled: "Runtime Error",
    SandboxStatus.FileError: "System Error",
    SandboxStatus.InternalError: "System Error",
}


# Request/Response Models
class FileInput(BaseModel):
    content: Optional[str] = None
    src: Optional[str] = None
    fileId: Optional[str] = None

    @model_validator(mode="after")
    def check_exactly_one(self):
        non_none_count = sum(1 for v in [self.content, self.src, self.fileId] if v is not None)
        if non_none_count != 1:
            raise ValueError("Exactly one of content, src, or fileId must be provided")
        return self


class TestcaseRequest(BaseModel):
    uuid: str
    input: FileInput
    output: FileInput

    def to_testcase(self) -> Testcase:
        from .models import LocalFile, MemoryFile, PreparedFile

        def parse_file(file_input: FileInput):
            if file_input.content is not None:
                return MemoryFile(file_input.content)
            elif file_input.src is not None:
                return LocalFile(file_input.src)
            elif file_input.fileId is not None:
                return PreparedFile(file_input.fileId)
            else:
                raise ValueError("Invalid file input")

        return Testcase(
            uuid=self.uuid,
            input=parse_file(self.input),
            output=parse_file(self.output)
        )


class JudgeRequest(BaseModel):
    timeLimit: int = Field(..., ge=1, description="Time limit in milliseconds")
    memoryLimit: int = Field(..., ge=1, description="Memory limit in kilobytes")
    testcases: list[TestcaseRequest] = Field(..., min_length=1, description="Test cases")
    language: int = Field(..., description="Language enum value")
    code: str = Field(..., min_length=1, description="Source code")
    type: int = Field(default=1, description="Problem type enum value")
    additionCode: str = Field(default="", description="Additional code for special judge")

    @model_validator(mode="after")
    def validate_language(self):
        try:
            Language(self.language)
        except ValueError:
            raise ValueError(f"Invalid language value: {self.language}")
        return self

    @model_validator(mode="after")
    def validate_type(self):
        try:
            ProblemType(self.type)
        except ValueError:
            raise ValueError(f"Invalid problem type value: {self.type}")
        return self

    def to_submission(self) -> Submission:
        return Submission(
            sid=random.randint(1, 999999),
            timeLimit=self.timeLimit,
            memoryLimit=self.memoryLimit,
            testcases=[tc.to_testcase() for tc in self.testcases],
            language=Language(self.language),
            code=self.code,
            type=ProblemType(self.type),
            additionCode=self.additionCode
        )


class TestcaseResultResponse(BaseModel):
    uuid: str
    time: int = 0
    memory: int = 0
    judgeResult: Literal[
        "Accepted",
        "Wrong Answer",
        "Presentation Error",
        "Time Limit Exceeded",
        "Memory Limit Exceeded",
        "Output Limit Exceeded",
        "Runtime Error",
        "Compile Error",
        "System Error",
        "Skipped"
    ]

    @classmethod
    def from_result(cls, result: TestcaseResult) -> "TestcaseResultResponse":
        return cls(
            uuid=result.uuid,
            time=result.time,
            memory=result.memory,
            judgeResult=_JUDGE_STATUS_MAP[result.judge]
        )


class JudgeResponse(BaseModel):
    time: int = 0
    memory: int = 0
    testcases: list[TestcaseResultResponse]
    judgeResult: Literal[
        "Accepted",
        "Wrong Answer",
        "Presentation Error",
        "Time Limit Exceeded",
        "Memory Limit Exceeded",
        "Output Limit Exceeded",
        "Runtime Error",
        "Compile Error",
        "System Error"
    ]
    compileError: str = ""

    @classmethod
    def from_result(cls, result: SubmissionResult) -> "JudgeResponse":
        return cls(
            time=result.time,
            memory=result.memory,
            testcases=[
                TestcaseResultResponse.from_result(tc)
                for tc in result.testcases
            ],
            judgeResult=_JUDGE_STATUS_MAP[result.judge],
            compileError=result.error
        )


# Run code models
class RunRequest(BaseModel):
    language: int = Field(..., description="Language enum value")
    code: str = Field(..., min_length=1, description="Source code")
    input: str = Field(default="", description="Standard input for the program")
    timeLimit: int = Field(default=DEFAULT_TIME_LIMIT // 1_000_000, description="Time limit in milliseconds")
    memoryLimit: int = Field(default=DEFAULT_MEMORY_LIMIT // 1024, description="Memory limit in kilobytes")

    @model_validator(mode="after")
    def validate_language(self):
        try:
            Language(self.language)
        except ValueError:
            raise ValueError(f"Invalid language value: {self.language}")
        return self


class RunResponse(BaseModel):
    compileStatus: Literal["Success", "Failed", "Not Needed"] = Field(
        ..., description="Compilation status"
    )
    compileError: str = Field(default="", description="Compilation error output if compilation failed")
    runStatus: Literal[
        "Accepted",
        "Time Limit Exceeded",
        "Memory Limit Exceeded",
        "Output Limit Exceeded",
        "Runtime Error",
        "System Error",
        "Compile Failed"
    ] = Field(..., description="Run status")
    exitStatus: int = Field(default=0, description="Process exit status")
    time: int = Field(..., description="Execution time in milliseconds")
    memory: int = Field(..., description="Memory usage in kilobytes")
    stdout: str = Field(default="", description="Standard output")
    stderr: str = Field(default="", description="Standard error output")


# Global client instance
_client: Optional[SandboxClient] = None


def get_client() -> SandboxClient:
    if _client is None:
        raise RuntimeError("SandboxClient not initialized")
    return _client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global _client

    sandbox_endpoint = os.getenv(
        "PTOJ_SANDBOX_ENDPOINT",
        "http://localhost:5050"
    )
    _client = SandboxClient(endpoint=sandbox_endpoint)
    logger.info("Connected to sandbox at %s", sandbox_endpoint)

    yield

    # Shutdown
    if _client is not None:
        await _client.close()
        logger.info("Disconnected from sandbox")


# Create FastAPI app
app = FastAPI(
    title="Putong OJ Judger API",
    description="Synchronous code judging service",
    version="2.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Putong OJ Judger API",
        "version": "2.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/judge", response_model=JudgeResponse)
async def judge(request: JudgeRequest, client: SandboxClient = Depends(get_client)) -> JudgeResponse:
    """
    Submit code for judging.

    This endpoint synchronously executes the submitted code against all test cases
    and returns the complete result.

    - **sid**: Unique submission identifier
    - **timeLimit**: Time limit per test case (milliseconds)
    - **memoryLimit**: Memory limit per test case (kilobytes)
    - **testcases**: List of test cases with input/output
    - **language**: Programming language (1=C, 2=Cpp11, 5=Cpp17, 3=Java, 6=PyPy, 4=Python)
    - **code**: Source code to execute
    - **type**: Problem type (1=Traditional, 2=Interaction, 3=SpecialJudge)
    - **additionCode**: Additional code for special judge/interactor

    Returns the complete judging result including status for each test case.
    """
    logger.info("Received judge request")

    try:
        submission = request.to_submission()
        judger = Judger(client=client, submission=submission)
        result = await judger.get_result()

        logger.info(
            "Submission %s completed with status: %s",
            submission.sid, result.judge.name
        )
        return JudgeResponse.from_result(result)

    except ValueError as e:
        logger.error("Validation error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Error processing submission: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Judging failed: %s" % str(e)
        )


@app.post("/run", response_model=RunResponse)
async def run(request: RunRequest, client: SandboxClient = Depends(get_client)) -> RunResponse:
    """
    Run code directly without judging.

    This endpoint compiles (if needed) and executes the submitted code,
    returning compilation status, execution status, and output.

    - **language**: Programming language (1=C, 2=Cpp11, 5=Cpp17, 3=Java, 6=PyPy, 4=Python)
    - **code**: Source code to execute
    - **input**: Standard input for the program (optional)
    - **timeLimit**: Time limit in milliseconds (default 10000)
    - **memoryLimit**: Memory limit in kilobytes (default 524288)

    Returns compilation result, execution status, and program output.
    """
    logger.info("Received run request for language %s", request.language)

    try:
        lang = Language(request.language)
        lang_config = LanguageRegistry.get_config(lang)

        compiled_file = None
        compile_status = "Not Needed"
        compile_error = ""

        # Compile if needed
        if lang_config.need_compile:
            logger.debug("Compiling code for language %s", lang)
            compile_status = "Success"

            compile_cmd = SandboxCmd(
                args=lang_config.compile_cmd,
                files=[
                    MemoryFile(""),
                    Collector("stdout"),
                    Collector("stderr")
                ],
                copyIn={
                    lang_config.source_filename: MemoryFile(request.code)
                },
                copyOutCached=[lang_config.compiled_filename]
            )

            compile_result = (await client.run_command([compile_cmd]))[0]

            if compile_result.status != SandboxStatus.Accepted:
                compile_status = "Failed"
                compile_error = compile_result.files.get("stderr", "")

                return RunResponse(
                    compileStatus=compile_status,
                    compileError=compile_error,
                    runStatus="Compile Failed",
                    exitStatus=compile_result.exitStatus,
                    time=0,
                    memory=0,
                    stdout="",
                    stderr=compile_error
                )

            compiled_file = PreparedFile(
                compile_result.fileIds[lang_config.compiled_filename]
            )
            logger.debug("Compilation successful")

        # Run the code
        logger.debug("Running code for language %s", lang)
        timeLimit = 1_000_000 * request.timeLimit * lang_config.time_factor
        memoryLimit = 1024 * request.memoryLimit * lang_config.memory_factor

        # Prepare runtime dependencies
        if lang_config.need_compile:
            copyIn = {lang_config.compiled_filename: compiled_file}
        else:
            copyIn = {lang_config.source_filename: MemoryFile(request.code)}

        run_cmd = SandboxCmd(
            args=lang_config.run_cmd,
            cpuLimit=timeLimit,
            clockLimit=timeLimit * 2,
            memoryLimit=memoryLimit,
            files=[
                MemoryFile(request.input) if request.input else None,
                Collector("stdout"),
                Collector("stderr")
            ],
            copyIn=copyIn,
            copyOut=["stdout", "stderr"]
        )

        run_result = (await client.run_command([run_cmd]))[0]

        # Extract output
        stdout = run_result.files.get("stdout", "") if run_result.files else ""
        stderr = run_result.files.get("stderr", "") if run_result.files else ""

        # Map SandboxStatus to run status string
        run_status_str = _SANDBOX_STATUS_MAP.get(run_result.status, "System Error")

        time_ms = min(run_result.time, timeLimit) // 1_000_000
        memory_kb = min(run_result.memory, memoryLimit) // 1024

        logger.info("Run completed with status: %s", run_status_str)

        # Cleanup compiled file
        if compiled_file:
            try:
                await client.delete_file(compiled_file.fileId)
            except Exception as e:
                logger.warning("Failed to delete compiled file: %s", e)

        return RunResponse(
            compileStatus=compile_status,
            compileError=compile_error,
            runStatus=run_status_str,
            exitStatus=run_result.exitStatus,
            time=time_ms,
            memory=memory_kb,
            stdout=stdout,
            stderr=stderr
        )

    except ValueError as e:
        logger.error("Validation error for run request: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Error processing run request: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Run failed: %s" % str(e)
        )
