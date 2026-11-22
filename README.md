# Tic-tac-toe API

A FastAPI backend for a human playing against a random or smart bot on a 3×3, 4×4, or 5×5 board.

## Run

Use Python 3.12+ and uv. From the repository root:

```shell
uv sync --locked --no-dev
uv run --no-sync python -m backend.main
```

Open `http://127.0.0.1:8000/` to play in the browser. The same server hosts the frontend and the REST API. Interactive API documentation is available at `http://127.0.0.1:8000/docs`. For local development with reload:

```shell
uv run uvicorn backend.presentation.api.entrypoint:create_app --factory --reload
```

## Play in the terminal

Run this command from the repository root to play in the terminal:

```shell
python -m backend.presentation.cli.entrypoint
```

## Docker Compose

From the repository root, run:

```shell
docker compose up --build
```

Open `http://127.0.0.1:8080/` to play and `http://127.0.0.1:8080/docs` for Swagger. Nginx serves the frontend and proxies the REST API to FastAPI on the private Compose network. Use `FRONTEND_PORT` in `.env` to change the published port. Compose sets the backend bind address and port internally.

After a frontend-only change, run `docker compose up -d --build --no-deps frontend` to rebuild that service while keeping the existing backend and its games.

## Game API

| Method | Path | Request and result |
| --- | --- | --- |
| POST | `/games` | An empty body starts a default game. Optional fields are `size`, `bot_mode` (`random` by default, or `smart`), and `previous_id` to replace a game. Returns 201 and the opening board. |
| GET | `/games/{game_id}` | Returns the last committed state, including the result of a finished game. |
| POST | `/games/{game_id}/moves` | Send zero-based integer coordinates such as `{"row": 0, "column": 1}`. Returns the board after the human move and any bot reply. |

An unknown game returns 404. An illegal move returns 409. Invalid request data returns 422. A failed bot turn leaves the last committed board available for retrieval.

## Operation

The backend runs with built-in defaults. To customize local settings, copy `.env.example` to `.env` in the repository root and edit the values.

The backend uses one process and one in-memory repository. Use a single worker and a single instance for this version. Restarting the process clears all games.

| Setting | Default | Purpose |
| --- | --- | --- |
| `BACKEND_HOST` | `127.0.0.1` | Bind address for the module entrypoint |
| `BACKEND_PORT` | `8000` | Bind port for the module entrypoint |
| `BACKEND_MAX_GAMES` | `10000` | Maximum stored games, including finished games |
| `BACKEND_BOT_SEARCH_BUDGET_MS` | `200` | Smart bot search budget on 4×4 and 5×5 (0–999 ms). At zero it still checks immediate wins and threats. On 3×3 it always uses exact search. |
| `BACKEND_APP_TITLE` | `Tic-Tac-Toe` | OpenAPI title |
| `BACKEND_LOG_LEVEL` | `INFO` | Backend diagnostic log level |
| `BACKEND_LOG_FORMAT` | `%(asctime)s %(levelname)s %(name)s %(message)s` | Backend log record format |
