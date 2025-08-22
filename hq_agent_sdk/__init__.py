"""
HQ Agent SDK - 一个用于LLM会话管理和工具调用的Python SDK
"""

from .llm_session import LLMSession, AgentConfig, ToolCall
from .function_to_tool_schema import function_to_tool_schema, python_type_to_schema
from .llm_client import BaseLLMClient, OpenAIClient, OllamaClient
from .tools.todos import create_todos, update_todos, query_todos, todos_before_hook, todos_after_hook
from .runner import BaseRunner, DefaultRunner

__version__ = "1.0.0"
__all__ = [
    "LLMSession",
    "AgentConfig",
    "ToolCall",
    "function_to_tool_schema",
    "python_type_to_schema",
    "BaseLLMClient",
    "OpenAIClient", 
    "OllamaClient",
    "create_todos",
    "update_todos",
    "query_todos",
    "todos_before_hook",
    "todos_after_hook",
    "BaseRunner",
    "DefaultRunner",
    "SimpleRunner",
    "SilentRunner"
]