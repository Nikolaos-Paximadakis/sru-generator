# Contributing

Thanks for considering a contribution to sru-generator.

## Setup

Dependency management is done via [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/Nikolaos-Paximadakis/sru-generator.git
cd sru-generator
uv sync --group dev
```

## Development workflow

```bash
uv run pytest tests/ -v --cov=sru_generator   # run tests with coverage
uv run flake8 sru_generator/ tests/
uv run black --check sru_generator/ tests/
uv run isort --check-only sru_generator/ tests/
uv run mypy sru_generator/ --ignore-missing-imports
```

All of the above run in CI; a PR won't pass review until they're clean.

## Submitting a change

1. Fork the repository and create a feature branch.
2. Make your changes, with tests covering new behavior.
3. Run the checks above locally.
4. Open a pull request describing what changed and why.

## Scope

This package is intentionally generic — see the "Boundary" section in
[CLAUDE.md](CLAUDE.md) for what belongs here versus in a consuming
application (broker lookups, DB access, taxpayer-profile storage, etc.
stay out of this package).
