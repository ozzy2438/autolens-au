# Contributing to AutoLens AU

Thank you for your interest in contributing to AutoLens AU!

## Development Setup

1. Fork and clone the repository
2. Create a virtual environment: `python -m venv .venv`
3. Install dependencies: `pip install -e ".[dev,dbt]"`
4. Copy `.env.example` to `.env` and configure
5. Run `pre-commit install` to set up git hooks

## Code Standards

- **Python**: Follow PEP 8; formatting and linting are enforced by `ruff`
- **SQL**: Use lowercase keywords, meaningful aliases
- **Tests**: Every new feature needs tests
- **Docs**: Update relevant documentation

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with clear commit messages
3. Add tests for new functionality
4. Run `make lint` and `make test`
5. Submit PR with description of changes
6. Tag if AI-assisted (see docs/AI_DELIVERY_LOG.md)

## Commit Message Convention

```
feat: add new feature
fix: fix a bug
docs: documentation only changes
test: add or update tests
chore: maintenance tasks
refactor: code refactoring
```

## Reporting Issues

Please use GitHub Issues for:
- Bug reports (include steps to reproduce)
- Feature requests
- Data quality observations
- UAT feedback

## Code of Conduct

Be respectful, constructive, and professional.
