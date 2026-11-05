"""
KURT Hub — Universal Skills, Agents, MCPs, Connectors

Integrates:
- aitmpl.com (909 skills, 422 agents, 111 MCPs, 288 commands, 63 hooks)
- Composio (250+ app connectors)
- awesome-mcp-servers (500+ community MCPs)
- LangChain (100+ tools)
- n8n (400+ workflow nodes)
"""

from .manager import hub_command, connect_command, hub_overview
from .aitmpl import hub_list, hub_search, hub_install, hub_stats
from .composio import composio_list, composio_connect, composio_status
from .mcp_servers import mcp_list, langchain_list, n8n_list, n8n_trigger

__all__ = [
    "hub_command",
    "connect_command",
    "hub_overview",
    "hub_list",
    "hub_search",
    "hub_install",
    "hub_stats",
    "composio_list",
    "composio_connect",
    "composio_status",
    "mcp_list",
    "langchain_list",
    "n8n_list",
    "n8n_trigger",
]
