# mcp-forge-core

Protocol-based framework for building MCP servers — clean interfaces, swappable providers.

## Install

```bash
pip install mcp-forge-core
```

## Quick Start

```python
from mcp_forge_core import create_mcp_app, run_server
from mcp_forge_core.providers import InMemoryCache

mcp = create_mcp_app("my-server", "A helpful MCP server")
run_server(mcp)
```

See the [mcp-forge repository](https://github.com/CoreNovus/mcp-forge) for full details.
