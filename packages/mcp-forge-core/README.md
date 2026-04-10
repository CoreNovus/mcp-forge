# mcp-forge-core

Protocol-based framework for building MCP servers — clean interfaces, swappable providers.

## Install

```bash
pip install mcp-forge-core
```

## Quick Start

```python
from mcp_forge_core import create_mcp_app
from mcp_forge_core.providers import InMemoryCache

mcp = create_mcp_app("my-server", "A helpful MCP server")
mcp.run()
```

See the [mcp-forge documentation](https://github.com/convilyn/mcp-forge) for full details.
