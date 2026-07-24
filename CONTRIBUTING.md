# Contributing to HWlogger

HWlogger accepts bug fixes, tests, documentation, and focused feature changes.
Keep sensor access read-only and platform-specific code isolated in backends.

## Setup

```bash
git clone https://github.com/your-account/HWlogger.git
cd HWlogger
./scripts/install-dev.sh
```

## Checks

Before opening a pull request:

```bash
.venv/bin/ruff check .
.venv/bin/pytest -q
HWLOGGER_SMOKE_TEST=1 ./scripts/run-dev.sh
```

Use type hints, dataclasses where appropriate, `pathlib`, and Python logging.
Do not commit user logs, local configuration, `.venv`, build artifacts,
credentials, tokens, machine-specific paths, or NVIDIA driver libraries.

Pull requests should describe the motivation, behavior change, test coverage,
and any impact on sensor compatibility or recording formats.
