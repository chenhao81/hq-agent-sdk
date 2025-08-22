"""
LLMSession 的运行器类
提供可自定义的输出处理功能，支持流式和非流式运行
"""

from abc import ABC, abstractmethod
from typing import Any, Generator, Union, Optional
from .llm_session import LLMSession


class BaseRunner(ABC):
    """
    Runner 基类，用于处理 LLMSession 的输出
    用户可以继承此类来自定义输出格式和行为
    """
    
    def __init__(self, session: LLMSession):
        """
        初始化 Runner
        
        Args:
            session: LLMSession 实例
        """
        self.session = session
    
    def run(self, user_message: Union[str, list] = None) -> Any:
        """
        运行会话，根据session的stream设置选择流式或非流式处理
        
        Args:
            user_message: 用户消息
            
        Returns:
            根据stream设置返回不同类型的结果
        """
        if self.session.stream:
            return self._run_streaming(user_message)
        else:
            return self._run_non_streaming(user_message)
    
    def _run_streaming(self, user_message: Union[str, list] = None) -> None:
        """
        流式运行处理
        
        Args:
            user_message: 用户消息
        """
        response_content = ""

        # 重置状态
        self.on_stream_start()
        
        # 开始流式调用
        stream_generator = self.session.call(user_message)
        
        for delta in stream_generator:
            # 处理 reasoning (思考过程)
            if hasattr(delta, 'reasoning') and delta.reasoning is not None:
                self.on_reasoning_delta(delta.reasoning)
            
            # 处理 content (回答内容)
            if hasattr(delta, 'content') and delta.content is not None and len(delta.content) > 0:
                self.on_content_delta(delta.content)
                response_content += delta.content
            
            # 处理 tool_calls
            if hasattr(delta, 'tool_calls') and delta.tool_calls is not None:
                for tool_call_delta in delta.tool_calls:
                    self.on_tool_call_delta(tool_call_delta)
        
        # 完成处理
        self.on_stream_end()

        return response_content
    
    def _run_non_streaming(self, user_message: Union[str, list] = None) -> Any:
        """
        非流式运行处理
        
        Args:
            user_message: 用户消息
            
        Returns:
            处理后的响应结果，不会产生中间思考和工具调用的内容
        """
        response = self.session.call(user_message)
        return self.on_response(response)
    
    # 抽象方法 - 子类必须实现
    
    @abstractmethod
    def on_stream_start(self) -> None:
        """流式输出开始时调用"""
        pass
    
    @abstractmethod
    def on_reasoning_delta(self, reasoning_text: str) -> None:
        """
        处理推理过程的增量文本
        
        Args:
            reasoning_text: 推理文本片段
        """
        pass
    
    @abstractmethod
    def on_content_delta(self, content_text: str) -> None:
        """
        处理回答内容的增量文本
        
        Args:
            content_text: 内容文本片段
        """
        pass
    
    @abstractmethod
    def on_tool_call_delta(self, tool_call_delta: Any) -> None:
        """
        处理工具调用的增量数据
        
        Args:
            tool_call_delta: 工具调用增量对象
        """
        pass
    
    @abstractmethod
    def on_stream_end(self) -> None:
        """流式输出结束时调用"""
        pass
    
    @abstractmethod
    def on_response(self, response: Any) -> Any:
        """
        处理非流式响应
        
        Args:
            response: 完整的响应对象
            
        Returns:
            处理后的结果
        """
        pass


class DefaultRunner(BaseRunner):
    """
    默认的 Runner 实现
    复现原始注释中的输出逻辑
    """
    
    def __init__(self, session: LLMSession):
        super().__init__(session)
        self.reset_state()
    
    def reset_state(self) -> None:
        """重置输出状态"""
        self.stage = 'pending'
    
    def on_stream_start(self) -> None:
        """流式输出开始时重置状态"""
        self.reset_state()
    
    def on_reasoning_delta(self, reasoning_text: str) -> None:
        """处理推理文本增量"""
        if self.stage != 'reasoning':
            print("\n🧠 思考过程:")
            self.stage = 'reasoning'
        print(reasoning_text, end="", flush=True)
    
    def on_content_delta(self, content_text: str) -> None:
        """处理内容文本增量"""
        if self.stage != 'content':
            print("\n🤖 模型回答:")
            self.stage = 'content'        
        print(content_text, end="", flush=True)
    
    def on_tool_call_delta(self, tool_call_delta: Any) -> None:
        """处理工具调用增量"""
        if self.stage != 'content':
            print("\n🔧 工具调用:")
            self.stage = 'content'        

        if hasattr(tool_call_delta, 'function') and tool_call_delta.function:
            if hasattr(tool_call_delta.function, 'name') and tool_call_delta.function.name:
                print(tool_call_delta.function.name, end="", flush=True)
            if hasattr(tool_call_delta.function, 'arguments') and tool_call_delta.function.arguments:
                print(tool_call_delta.function.arguments, end="", flush=True)
    
    def on_stream_end(self) -> None:
        """流式输出结束"""
        print("\n")
    
    def on_response(self, response: Any) -> Any:
        """处理非流式响应"""
        if hasattr(response, 'message') and hasattr(response.message, 'content'):
            print("🤖 AI回复:", response.message.content)
        else:
            print("🤖 AI回复:", str(response))
        return response

