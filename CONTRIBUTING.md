# Contributing to mcp-forge

## Quick Start

```bash
git clone https://github.com/CoreNovus/mcp-forge.git
cd mcp-forge
pip install -e packages/mcp-forge-core[dev]
pip install -e packages/mcp-forge-aws[dev]
pip install -e packages/mcp-forge-cli[dev]
```

## Workflow

1. Fork the repo
2. Create a branch from `main`
3. Make changes, add tests
4. Run `ruff check packages/` and `pytest`
5. Open a PR — CI must pass and 1 review is required

## Rules

- Every PR needs tests
- `ruff check` must pass
- No business-specific code — this is a generic framework
- Keep provider ABCs domain-agnostic

## Package Structure

- `mcp-forge-core` — infrastructure providers, patterns, server factory
- `mcp-forge-aws` — AWS implementations (Bedrock, DynamoDB, CloudWatch)
- `mcp-forge-cli` — scaffold CLI tool
