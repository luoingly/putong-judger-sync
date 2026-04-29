# Putong AI Overseer

A CLI tool for evaluating AI models' ability to solve algorithm problems via Virtual Judge. It securely executes submitted code using the [go-judge](https://github.com/criyle/go-judge) sandbox.

## Getting Started 🚀

### Prerequisites

Ensure that you have [Docker](https://www.docker.com/) installed on your server.

Additionally, install the required dependencies:

```bash
pip install uv
uv sync
```

### Configure Settings

Create `data/models.yaml` with your AI model credentials:

```yaml
models:
  - name: "your-model"
    base_url: "https://api.example.com"
    api_key: "sk-..."
    temperature: 0.2
    max_tokens: 4096
```

### Build and Run

#### Build Docker Images

Run the following commands to build and start the sandbox:

```bash
docker build . -f Dockerfile.sandbox -t go-judge
docker run -d --privileged -p 5050:5050 --name go-judge go-judge
```

#### Run the Overseer

```bash
# Single model, single problem
uv run python run.py --model your-model --problem a-plus-b --language python

# Multiple models comparison
uv run python run.py --model gpt-4o --model claude-sonnet --problem a-plus-b --language python

# Multiple problems
uv run python run.py --model your-model --problem a-plus-b --problem two-sum --language cpp17

# Tool agent (multi-turn with tool calling)
uv run python run.py --model your-model --problem a-plus-b --language python --agent tool
```

### CLI Options

| Option           | Description                                          | Default                 |
| ---------------- | ---------------------------------------------------- | ----------------------- |
| `--model`        | Model name (from config), repeatable                 | required                |
| `--problem`      | Problem ID, repeatable                               | required                |
| `--language`     | `c` / `cpp11` / `cpp17` / `java` / `python` / `pypy` | required                |
| `--agent`        | `simple` (single-turn) or `tool` (multi-turn)        | `simple`                |
| `--sandbox`      | Sandbox endpoint                                     | `http://localhost:5050` |
| `--max-turns`    | Max turns for tool agent                             | `10`                    |
| `--config`       | Models config file                                   | `data/models.yaml`      |
| `--problems-dir` | Problems directory                                   | `data/problems`         |

## Problem Format 📝

Each problem is a directory under `data/problems/`:

```text
data/problems/a-plus-b/
├── problem.yaml       # Constraints
├── description.md     # Problem statement
├── addition.cpp       # [Optional] For interaction/special-judge
└── tests/
    ├── sample-1.in
    ├── sample-1.out
    └── ...
```

**problem.yaml:**

```yaml
title: "A + B Problem"
source: "Example"
constraints:
  timeLimit: 1000       # ms
  memoryLimit: 32768    # KB
  problemType: traditional  # traditional / interaction / special-judge
```

Test cases are auto-discovered by matching `*.in` / `*.out` pairs in `tests/`.

For `interaction` or `special-judge` type, place `addition.cpp` in the problem directory.

## Output 📊

Each run saves results to `data/records/{timestamp}/`:

- `{model}__{problem}.json` — Full record with conversation trace, tool calls, token usage, and judge details
- `run.yaml` — Summary of all results

## Development 🛠️

Run the following commands to lint and format code:

```bash
# Lint & format
uv run ruff check --fix
uv run ruff format
```

## License 📜

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
