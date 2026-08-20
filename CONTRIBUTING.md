# Contributing to lambda-cloud-cli

Thanks for helping the community! Here is the short version:

## Setup

```bash
git clone https://github.com/mrprokl/lambda-cloud-cli.git
cd lambda-cloud-cli
uv venv
uv pip install -e '.[dev]'
```

## Checks to run before opening a PR

```bash
uv run ruff check --fix src tests
uv run pytest --cov
```

## Guidelines

- **No secrets in the repo, ever.** The test suite never performs real
  network calls: mock the API with [`respx`](https://lundberg.github.io/respx/).
- Keep the layered architecture; dependencies flow strictly downward:

  ```
  cli/commands → cli/ui → api (client/service) → core / mngr
  ```

  New endpoint? Add the function to `api/service.py`, the table to
  `cli/ui/tables.py`, the command to `cli/commands/`, and tests under `tests/`.
- Keep models tolerant to API additions (`extra="ignore"` in
  `mngr/models.py`).
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/):
  `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`.
- Public API and behaviors are documented in the README: keep it in sync.

## Reporting issues

Include: the command you ran, the output (use `--output json` when useful),
your Python version (`python --version`) and the CLI version
(`lambda-cloud --version`). Never paste your API key.
