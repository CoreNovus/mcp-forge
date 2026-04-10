# Contributing to mcp-forge

We'd love your help making mcp-forge better. Whether it's a bug fix, new provider, or documentation improvement — all contributions are welcome.

## Getting Started

```bash
# 1. Fork this repo on GitHub, then:
git clone git@github.com:<your-username>/mcp-forge.git
cd mcp-forge

# 2. Install everything
pip install -e packages/mcp-forge-core[dev]
pip install -e packages/mcp-forge-aws[dev]
pip install -e packages/mcp-forge-cli[dev]

# 3. Make sure it works
ruff check packages/
pytest packages/mcp-forge-core/tests/
pytest packages/mcp-forge-aws/tests/
pytest packages/mcp-forge-cli/tests/
```

That's it. You're ready to contribute.

## How to Contribute

### 1. Pick something to work on

- Browse [open issues](https://github.com/CoreNovus/mcp-forge/issues)
- Look for `good first issue` labels if this is your first contribution
- Or just fix something that bothers you

### 2. Create a branch and make your changes

```bash
git checkout -b feat/your-idea       # feature
git checkout -b fix/what-you-fixed   # bug fix
git checkout -b docs/what-you-added  # docs
```

### 3. Write tests

Every change needs tests. We aim for real boundary testing — not just happy paths:

```python
# Good: tests the edge case
async def test_cache_empty_string_key(self, cache):
    await cache.put("", {"v": 1})
    assert await cache.get("") == {"v": 1}

# Good: tests error behavior
async def test_unknown_type_raises(self):
    with pytest.raises(ValueError, match="Unknown"):
        await provider.extract(b"img", "nonexistent")
```

### 4. Run checks, then open a PR

```bash
ruff check packages/                      # lint
pytest packages/mcp-forge-core/tests/     # core tests
pytest packages/mcp-forge-aws/tests/      # aws tests
pytest packages/mcp-forge-cli/tests/      # cli tests
```

Push your branch, open a PR, and fill in the template. CI runs automatically — once it's green and reviewed, we'll merge it.

## What Goes Where

| Package | What belongs here |
|---------|------------------|
| **mcp-forge-core** | Provider ABCs, config, server factory, ToolContext, decorators, resilience patterns. Pure Python, zero cloud dependencies. |
| **mcp-forge-aws** | AWS-specific implementations. Depends on boto3. |
| **mcp-forge-cli** | Scaffold CLI and Jinja2 templates. |

## Things to Keep in Mind

**Framework, not application.** mcp-forge is used by many different MCP servers. Don't add code that assumes a specific use case (document processing, image analysis, etc.).

**Provider ABCs are domain-agnostic.** Infrastructure providers (Cache, Session, Telemetry) are top-level exports. Capability providers (Vision, Transcribe) exist for swappability but are direct-import only — the framework doesn't assume everyone needs them.

**Tests matter.** We test boundaries: empty input, unicode, TTL expiry, error propagation, concurrent access. If you find an untested edge case, that's a great first PR.

**Keep it simple.** If your change adds complexity, make sure it solves a real problem. Three lines of clear code beats a clever abstraction.

## Questions?

Open an [issue](https://github.com/CoreNovus/mcp-forge/issues). There are no dumb questions.
