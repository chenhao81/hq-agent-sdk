import json
from openai import OpenAI
from typing import Dict, List, Callable, Optional, Any, Generator, Union
from dataclasses import dataclass
from .function_to_tool_schema import function_to_tool_schema


@dataclass
class AgentConfig:
    """Agent配置类"""
    model: str = "gpt-oss:20b"
    max_iterations: int = 5
    temperature: float = 0.1
    max_tokens: Optional[int] = None
    timeout: float = 30.0


class ToolCall:
    """工具调用对象"""
    def __init__(self):
        self.id: str = ""
        self.type: str = "function"
        self.function = type('', (), {'name': '', 'arguments': ''})()


class LLMSession:
    """LLM Session 类，支持工具调用和流式输出"""
    
    def __init__(
        self,
        client: OpenAI,
        tools: List[Callable] = None,
        config: AgentConfig = None,
        stream: bool = True,
        system_prompt: str = "你是一个AI助手"
    ):
        """
        初始化 LLMSession
        
        Args:
            client: OpenAI客户端对象
            tools: 工具函数列表
            config: 配置参数
            stream: 是否使用流式输出
            system_prompt: 系统提示词
        """
        self.client = client
        self.config = config or AgentConfig()
        self.stream = stream
        self.system_prompt = system_prompt
        
        # 初始化消息历史
        self.messages = [{"role": "system", "content": system_prompt}]
        
        # 处理工具函数
        self.tools = tools or []
        self.tool_functions = {}
        self.tools_description = []
        
        for tool_func in self.tools:
            # 构建工具描述
            tool_schema = {
                "type": "function",
                "function": function_to_tool_schema(tool_func)
            }
            self.tools_description.append(tool_schema)
            
            # 构建函数映射
            self.tool_functions[tool_func.__name__] = tool_func
    
    def add_user_message(self, content: str):
        """添加用户消息"""
        self.messages.append({"role": "user", "content": content})
    
    def add_system_message(self, content: str):
        """添加系统消息"""
        self.messages.append({"role": "system", "content": content})
    
    def clear_messages(self):
        """清空消息历史，保留系统提示"""
        self.messages = [{"role": "system", "content": self.system_prompt}]
    
    def _execute_tool_call(self, tool_call: ToolCall) -> str:
        """执行工具调用"""
        try:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            if function_name in self.tool_functions:
                result = self.tool_functions[function_name](**function_args)
                return str(result)
            else:
                return f"错误: 未找到工具函数 {function_name}"
                
        except json.JSONDecodeError as e:
            return f"错误: 参数解析失败 - {str(e)}"
        except Exception as e:
            return f"错误: 工具执行失败 - {str(e)}"
    
    def _parse_streaming_response(self, stream_response) -> Generator[Any, None, Dict]:
        """解析流式响应"""
        content = ""
        reasoning = ""
        tool_calls = []
        
        for chunk in stream_response:
            delta = chunk.choices[0].delta
            
            # 向外输出原始delta
            yield delta
            
            # 收集reasoning
            if hasattr(delta, 'reasoning') and delta.reasoning is not None:
                reasoning += delta.reasoning
            
            # 收集content
            if hasattr(delta, 'content') and delta.content is not None:
                content += delta.content
            
            # 收集tool_calls
            if hasattr(delta, 'tool_calls') and delta.tool_calls is not None:
                for tool_call_delta in delta.tool_calls:
                    index = tool_call_delta.index
                    
                    # 确保tool_calls列表足够长
                    while len(tool_calls) <= index:
                        tool_calls.append(None)
                    
                    if tool_calls[index] is None:
                        tool_calls[index] = ToolCall()
                    
                    # 更新工具调用信息
                    if hasattr(tool_call_delta, 'id') and tool_call_delta.id:
                        tool_calls[index].id = tool_call_delta.id
                    
                    if hasattr(tool_call_delta, 'function') and tool_call_delta.function:
                        if hasattr(tool_call_delta.function, 'name') and tool_call_delta.function.name:
                            tool_calls[index].function.name += tool_call_delta.function.name
                        if hasattr(tool_call_delta.function, 'arguments') and tool_call_delta.function.arguments:
                            tool_calls[index].function.arguments += tool_call_delta.function.arguments
        
        # 返回收集到的完整响应
        return {
            'content': content,
            'reasoning': reasoning,
            'tool_calls': [tc for tc in tool_calls if tc is not None]
        }
    
    def _handle_tool_calls(self, tool_calls: List[ToolCall], assistant_content: str) -> bool:
        """处理工具调用，返回是否有工具被执行"""
        if not tool_calls:
            return False
        
        # 添加助手消息
        assistant_message = {
            "role": "assistant",
            "content": assistant_content if assistant_content else None
        }
        
        # 添加工具调用信息
        assistant_message["tool_calls"] = []
        for tc in tool_calls:
            assistant_message["tool_calls"].append({
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            })
        
        self.messages.append(assistant_message)
        
        # 执行工具调用并添加结果
        for tc in tool_calls:
            tool_result = self._execute_tool_call(tc)
            self.messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": tool_result
            })
        
        return True
    
    def call(self, user_message: str = None) -> Union[Generator[Any, None, None], Any]:
        """
        调用LLM，支持工具调用的完整流程
        
        Args:
            user_message: 用户消息，如果提供则添加到消息历史
            
        Returns:
            如果是流式输出，返回Generator，产出delta对象
            如果不是流式输出，返回最终的choices[0]对象
        """
        if user_message:
            self.add_user_message(user_message)
        
        if self.stream:
            return self._call_streaming()
        else:
            return self._call_non_streaming()
    
    def _call_streaming(self) -> Generator[Any, None, None]:
        """流式调用"""
        iteration = 0
        
        while iteration < self.config.max_iterations:
            iteration += 1
            
            # 创建流式请求
            stream_response = self.client.chat.completions.create(
                model=self.config.model,
                messages=self.messages,
                tools=self.tools_description if self.tools_description else None,
                stream=True,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            # 解析流式响应
            response_data = yield from self._parse_streaming_response(stream_response)
            
            # 处理工具调用
            if response_data['tool_calls']:
                tool_executed = self._handle_tool_calls(
                    response_data['tool_calls'], 
                    response_data['content']
                )
                if tool_executed:
                    continue  # 继续下一轮对话
            else:
                # 没有工具调用，添加最终的助手消息
                if response_data['content']:
                    self.messages.append({
                        "role": "assistant",
                        "content": response_data['content']
                    })
                break
        
        # 流式输出完成，不需要返回值
        return
    
    def _call_non_streaming(self) -> Any:
        """非流式调用"""
        iteration = 0
        final_response = None
        
        while iteration < self.config.max_iterations:
            iteration += 1
            
            # 创建非流式请求
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=self.messages,
                tools=self.tools_description if self.tools_description else None,
                stream=False,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            final_response = response.choices[0]
            message = final_response.message
            
            # 检查是否有工具调用
            if hasattr(message, 'tool_calls') and message.tool_calls:
                # 添加助手消息
                assistant_message = {
                    "role": "assistant",
                    "content": message.content
                }
                
                # 添加工具调用信息
                assistant_message["tool_calls"] = []
                for tc in message.tool_calls:
                    assistant_message["tool_calls"].append({
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    })
                
                self.messages.append(assistant_message)
                
                # 执行工具调用
                for tc in message.tool_calls:
                    # 创建兼容的ToolCall对象
                    tool_call_obj = ToolCall()
                    tool_call_obj.id = tc.id
                    tool_call_obj.function.name = tc.function.name
                    tool_call_obj.function.arguments = tc.function.arguments
                    
                    tool_result = self._execute_tool_call(tool_call_obj)
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": tool_result
                    })
                
                continue  # 继续下一轮对话
            else:
                # 没有工具调用，添加最终消息并结束
                self.messages.append({
                    "role": "assistant",
                    "content": message.content
                })
                break
        
        return final_response