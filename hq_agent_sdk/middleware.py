"""
中间件系统，用于处理工具调用的前置和后置逻辑
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import threading


class ToolMiddleware(ABC):
    """工具中间件抽象基类"""
    
    @abstractmethod
    def before_tool_call(self, tool_name: str, args: Dict[str, Any], session) -> Dict[str, Any]:
        """
        工具调用前的处理
        
        Args:
            tool_name: 工具函数名称
            args: 工具调用参数
            session: LLMSession实例
            
        Returns:
            处理后的参数字典
        """
        pass
    
    def after_tool_call(self, result: Any, tool_name: str, session) -> Any:
        """
        工具调用后的处理
        
        Args:
            result: 工具调用结果
            tool_name: 工具函数名称
            session: LLMSession实例
            
        Returns:
            处理后的结果
        """
        return result


class TodosMiddleware(ToolMiddleware):
    """Todos工具专用中间件，自动注入session_id"""
    
    def before_tool_call(self, tool_name: str, args: Dict[str, Any], session) -> Dict[str, Any]:
        """为todos相关工具自动注入session_id"""
        if tool_name in ['create_todos', 'update_todos', 'query_todos']:
            # 自动注入session_id
            args = args.copy()  # 避免修改原始参数
            args['session_id'] = session.session_id
        return args
    
    def after_tool_call(self, result: Any, tool_name: str, session) -> Any:
        return result


class MiddlewareManager:
    """中间件管理器"""
    
    def __init__(self):
        self.middlewares: List[ToolMiddleware] = []
    
    def add_middleware(self, middleware: ToolMiddleware):
        """添加中间件"""
        self.middlewares.append(middleware)
    
    def process_before_tool_call(self, tool_name: str, args: Dict[str, Any], session) -> Dict[str, Any]:
        """执行所有中间件的before_tool_call"""
        processed_args = args
        for middleware in self.middlewares:
            processed_args = middleware.before_tool_call(tool_name, processed_args, session)
        return processed_args
    
    def process_after_tool_call(self, result: Any, tool_name: str, session) -> Any:
        """执行所有中间件的after_tool_call（逆序执行）"""
        processed_result = result
        for middleware in reversed(self.middlewares):
            processed_result = middleware.after_tool_call(processed_result, tool_name, session)
        return processed_result