# Putong OJ - Judger API

![Python](https://img.shields.io/badge/python-%3E%3D3.11-3572a5)
[![Test Status](https://img.shields.io/github/actions/workflow/status/net-escape/ptoj-judger/ci.yml?label=test)](https://github.com/net-escape/ptoj-judger/actions/workflows/ci.yml)
[![Codecov](https://img.shields.io/codecov/c/github/net-escape/ptoj-judger/main)](https://app.codecov.io/github/net-escape/ptoj-judger)
[![GitHub License](https://img.shields.io/github/license/net-escape/ptoj-judger)](https://github.com/net-escape/ptoj-judger/blob/main/LICENSE)

A synchronous HTTP API for code execution and judging, designed for programming contest platforms and online judges. It securely executes submitted code using the [go-judge](https://github.com/criyle/go-judge) sandbox.

## API Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation (Swagger UI)

## Getting Started 🚀

### Prerequisites

Ensure that you have the [Docker](https://www.docker.com/) installed on your server.

Additionally, you need to have a running instance of [Putong OJ](https://github.com/net-escape/ptoj-backend).

### Build and Run

1. **Build and start the sandbox:**
```bash
docker build . -f Dockerfile.sandbox -t go-judge
docker run -d --privileged -p 5050:5050 --name go-judge go-judge
```

2. **Run the judger API:**
```bash
docker build . -f Dockerfile.judger -t ptoj-judger
docker run -d -p 8000:8000 \
  -e PTOJ_SANDBOX_ENDPOINT=http://host.docker.internal:5050 \
  --name ptoj-judger \
  ptoj-judger
```

### Local Development

1. **Install dependencies:**
```bash
pip install uv
uv sync --all-extras
```


### Environment Variables

| Variable                | Description          | Default                 |
| ----------------------- | -------------------- | ----------------------- |
| `PTOJ_SANDBOX_ENDPOINT` | Sandbox endpoint URL | `http://localhost:5050` |
| `PTOJ_HOST`             | API server host      | `0.0.0.0`               |
| `PTOJ_PORT`             | API server port      | `8000`                  |
| `PTOJ_LOG_FILE`         | Log file path        | `judger.log`            |
| `PTOJ_DEBUG`            | Debug mode (0/1)     | `1`                     |

## Development 🛠️

### Prerequisites

Install the required dependencies:

```bash
uv sync --all-extras
```

### Running the Judger Locally

```bash
uv run python main.py
```

### Testing

Run the following command to execute the test suite:

```bash
uv run pytest --cov=judger
```

For more details, check the [tests](tests) directory.

## License 📜

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
