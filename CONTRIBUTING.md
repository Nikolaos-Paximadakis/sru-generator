# Contributing

Thanks for considering a contribution to sru-generator.

## Setup

Dependency management is done with [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/Nikolaos-Paximadakis/sru-generator.git
cd sru-generator
uv sync --group dev
```

## Checks

```bash
uv run ruff check .            # lint (add --fix for the safe fixes)
uv run ruff format --check .   # formatting
uv run mypy                    # strict type check of the package and tests
uv run pytest --cov            # tests; warnings are errors
```

All of these run in CI on Python 3.11–3.14; a pull request needs them green.
`uv run pre-commit install` runs ruff and mypy before each commit.

## Submitting a change

1. Fork the repository and create a branch.
2. Make the change, with tests for new behaviour. If the written file changes, the
   golden files in `tests/golden/` must change with it, and the pull request should
   say why.
3. Cite the source (a Skatteverket URL) for any rule you implement.
4. Add a line to `CHANGELOG.md` and open a pull request describing what changed and why.

## Privacy

Never commit or post a real personnummer, name, SRU file or trade export, not even in
a test or an issue. Use made-up data. `*.sru`/`*.SRU` files are git-ignored for this
reason; only the synthetic files in `tests/golden/` are tracked.

## Scope

This package stays generic: it formats figures into SRU files and validates them.
These belong in the application that uses it, not here:

- broker-specific parsing (Avanza, Nordnet, IBKR, exchanges...)
- fetching exchange rates or other network access
- databases, storage paths, or loading taxpayer profiles
- tax decisions such as the cost-basis method or which K4 section an asset belongs in

## Code of conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
