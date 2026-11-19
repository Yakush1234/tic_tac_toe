# Project & Stack

- These instructions apply throughout the repository. Read `PROJECT_PLAN.md` for the agreed game rules, scope, and proposed layout.
- Use Python 3.12+ and `uv` for environment and package management. The current project declares no third-party dependencies.
- The backend follows clean/onion architecture. FastAPI is planned for the HTTP layer. Frontend work follows the backend, and its stack is still open.

## Architecture

- Keep `backend/domain/` independent of the other layers. Use only the Python standard library there.
- Keep board and game rules in `domain/entities/`, domain contracts such as `BotStrategy` in `domain/interfaces/`, and shared enums and immutable values in `domain/enums.py` and `domain/values.py`. Both human and bot moves go through `Game.play`.
- Use `backend/application/` for use cases and the contracts they need for persistence. Put concrete storage in `backend/infrastructure/`, HTTP handling in `backend/presentation/`, and component wiring in `backend/main.py`. Work only on the layers requested for the current task.

## Python Conventions

- Use absolute imports rooted at `backend`, such as `from backend.domain.values import Position`. Use `pathlib.Path` for filesystem paths.
- Write comments, docstrings, exception messages, and other strings in Python code in English.
- Give every module, class, function, method, and property an English docstring. In the domain, document the game rule or contract, including meaningful outcomes and invalid moves.
- Annotate all parameters and return types, including `self: Self` on instance methods and `-> None` on constructors and methods that return nothing. Annotate fields, instance attributes, and named local variables. Declare each enum's underlying value type with `_value_: int` or `_value_: str`, as appropriate.
- Follow the Ruff configuration in `pyproject.toml`. Reuse existing domain types, helpers, and exceptions before introducing new ones.

## Commands

Run commands from the repository root.

| Task | Command | When to use |
| --- | --- | --- |
| Set up the environment | `uv sync --locked` | When environment setup is requested |
| Check Python syntax | `python -m compileall -q backend` | After Python changes, using Python 3.12+ |
| Run standard-library tests | `python -m unittest discover -s tests` | When a discoverable unittest suite exists under `tests/` |
| Lint | `uv run --no-sync ruff check .` | With Ruff already available |
| Check formatting | `uv run --no-sync ruff format --check .` | With Ruff already available |
| Check types | `uv run --no-sync mypy backend` | With mypy already available. Include `tests` once that directory exists |
| Run pytest tests | `uv run --no-sync pytest` | With pytest already available and relevant tests present |

## Constraints & Definition of Done

- Add or install dependencies only when explicitly requested. Ruff has project configuration, but Ruff, mypy, and pytest are not declared dependencies. Use available tools and report any checks you could not run.
- Preserve generated files, `.env`, and existing migrations unless explicitly asked to change them. Let `uv` manage `uv.lock` for authorized dependency changes.
- For Python changes, check syntax, run the available lint, format, and type checks, and exercise the affected behavior. If a test suite exists, run the relevant tests. Until then, use focused standard-library checks. For domain rule changes, cover both a valid move and the affected boundary or terminal case.
- For documentation-only changes, verify the text against the project layout, configuration, and agreed requirements.
