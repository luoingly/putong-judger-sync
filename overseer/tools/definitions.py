from overseer.provider import ToolDef

READ_PROBLEM = ToolDef(
    name="read_problem",
    description="Read the full problem statement and constraints.",
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    },
)

SUBMIT_CODE = ToolDef(
    name="submit_code",
    description=(
        "Submit code for full judging against all test cases. "
        "Returns the verdict (Accepted, Wrong Answer, etc.) and per-testcase details."
    ),
    parameters={
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The source code to submit",
            },
        },
        "required": ["code"],
    },
)

RUN_CODE = ToolDef(
    name="run_code",
    description=(
        "Run code with custom input without judging. "
        "Useful for debugging. Returns stdout, stderr, and execution status."
    ),
    parameters={
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The source code to run",
            },
            "input": {
                "type": "string",
                "description": "The input to feed to the program",
            },
        },
        "required": ["code", "input"],
    },
)

ALL_TOOLS = [READ_PROBLEM, SUBMIT_CODE, RUN_CODE]
