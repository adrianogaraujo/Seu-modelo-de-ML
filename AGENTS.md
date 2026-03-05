# Repository Guidelines

## Project Structure & Module Organization
The application code lives under `src/` and is organized by responsibility. Use `src/api` for FastAPI entrypoints, request/response schemas, and route wiring. Keep the Streamlit interface in `src/app`. Source connectors belong in `src/ingestion`, dataset shaping in `src/processing`, model training and inference in `src/modeling`, orchestration flows in `src/jobs`, runtime configuration in `src/config`, and persistence logic in `src/storage`.

Tests mirror the runtime architecture. Put isolated logic checks in `tests/unit`, cross-module behavior in `tests/integration`, and endpoint or end-to-end workflow validation in `tests/e2e`. Local runtime outputs such as SQLite files, CSV snapshots, and model artifacts live in `data/`. Container assets live in `infra/`.

## Build, Test, and Development Commands
Run all commands from `project/` unless noted otherwise.

- `python -m venv .venv`: create a local virtual environment.
- `.venv\Scripts\activate`: activate the virtual environment on Windows PowerShell.
- `pip install -r requirements.txt`: install runtime and test dependencies.
- `python -m unittest discover -s tests`: run the full automated suite.
- `python -m unittest discover -s tests -p "test_*.py"`: run the default discovery pattern explicitly.
- `python -m unittest tests.unit.test_features`: run a narrow test target first while iterating.
- `uvicorn src.api.main:app --reload`: start the API in local development mode.
- `python -m src.jobs.run_real_acceptance`: execute the real-source acceptance workflow from the CLI.

From `infra/`, use `docker compose up --build` to boot the API and Streamlit app together for a local stack check.

## Coding Style & Naming Conventions
Use Python with 4-space indentation and keep code ASCII unless the file already requires otherwise. Follow `snake_case` for modules, functions, variables, and most filenames. Use `PascalCase` for classes and API schema models. Prefer short, explicit functions with clear inputs and outputs over large multi-step procedures.

Keep HTTP handlers thin. Validation, transformation, model logic, and persistence should stay outside route files whenever possible. If a new feature spans multiple layers, keep each layer focused on one concern instead of embedding the full workflow in one file.

## Testing Guidelines
`unittest` is the project standard, and TDD is the default workflow for code changes.

1. Write or update the narrowest failing test that proves the intended behavior.
2. Run the smallest relevant suite first, usually a single unit test module.
3. Implement the minimum code needed to make the test pass.
4. Refactor only after the targeted tests are green.
5. Run the broader suite before finishing the change.

Every behavior change should include test coverage unless the change is strictly documentation or a non-functional config update. Bug fixes should start with a regression test. Match existing naming: `test_*.py` files, `test_*` methods, and placement in the narrowest applicable test folder.

## Commit & Pull Request Guidelines
Follow the style already present in history: concise, imperative, Conventional Commit-like messages such as `feat: add acceptance validation` or `fix: guard empty source payload`. Keep each commit focused on one logical change.

Pull requests should explain the purpose of the change, list the modules touched, and summarize how the change was validated. Include test commands you ran, note any required `.env` or source changes, and attach screenshots for Streamlit updates or sample request/response payloads for API changes.

## Security & Configuration Tips
Use `.env.example` as the source of truth for required configuration. Real-source execution depends on `BCB_*`, `SIDRA_*`, and `CAGED_*` variables being present. Keep `APP_ENV=prod` for strict real-data execution. Only enable `ALLOW_SYNTHETIC_DATA=1` during local development, and only with `APP_ENV=dev`, `local`, or `test`. Do not commit `.env`, local database files, generated CSVs, cached outputs, or model artifacts from `data/`.

If you introduce a new external source, document the required environment variables and failure mode in the same change that adds the connector.
