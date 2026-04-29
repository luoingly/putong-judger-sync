from overseer.provider import ToolDef

READ_PROBLEM = ToolDef(
    name="read_problem",
    description="阅读完整的题目描述和限制条件。",
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    },
)

SUBMIT_CODE = ToolDef(
    name="submit_code",
    description=(
        "提交代码进行完整评测，会对所有测试点进行评判。"
        "返回评测结果（Accepted、Wrong Answer 等）及每个测试点的详细信息。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "要提交的源代码",
            },
        },
        "required": ["code"],
    },
)

RUN_CODE = ToolDef(
    name="run_code",
    description=(
        "使用自定义输入运行代码，不进行评测。适合调试使用。返回标准输出、标准错误和运行状态。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "要运行的源代码",
            },
            "input": {
                "type": "string",
                "description": "程序的输入数据",
            },
        },
        "required": ["code", "input"],
    },
)

ALL_TOOLS = [READ_PROBLEM, SUBMIT_CODE, RUN_CODE]
