"""
HQ Agent SDK - 一个用于LLM会话管理和工具调用的Python SDK
"""

from .llm_session import LLMSession, AgentConfig, ToolCall
from .function_to_tool_schema import function_to_tool_schema, python_type_to_schema

__version__ = "1.0.0"
__all__ = [
    "LLMSession",
    "AgentConfig", 
]