import json
import uuid
import re
import os
import logging
from datetime import datetime
from typing import Dict, List, Callable, Optional, Any, Generator, Union, Tuple
from dataclasses import dataclass

try:
    import json5
except ImportError:
    json5 = None
from .function_to_tool_schema import function_to_tool_schema
from .llm_client import BaseLLMClient

@dataclass
class AgentConfig:
    """Agent配置类"""
    model: str = "gpt-oss:20b"
    max_iterations: int = 100
    temperature: float = 0.1
    max_tokens: Optional[int] = None
    timeout: float = 30.0
    response_format: Optional[Dict[str, str]] = None


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
        client: BaseLLMClient,
        tools: List[Callable] = None,
        config: AgentConfig = None,
        stream: bool = True,
        system_prompt: str = "你是一个AI助手",
        before_tool_calling: List[Callable] = None,
        after_tool_calling: List[Callable] = None,
        enable_logging: bool = True
    ):
        """
        初始化 LLMSession
        
        Args:
            client: LLM客户端对象（支持OpenAI或Ollama）
            tools: 工具函数列表
            config: 配置参数
            stream: 是否使用流式输出
            system_prompt: 系统提示词
            before_tool_calling: 工具调用前执行的函数列表
            after_tool_calling: 工具调用后执行的函数列表
            enable_logging: 是否启用日志记录
        """
        self.client = client
        self.config = config or AgentConfig()
        self.stream = stream
        self.system_prompt = system_prompt

        # 生成唯一的session_id
        self.session_id = str(uuid.uuid4())
        
        # 初始化日志功能
        self.enable_logging = enable_logging
        self.logger = None
        if self.enable_logging:
            self._setup_logger()
        
        # 初始化前置和后置函数列表
        self.before_tool_calling = before_tool_calling or []
        self.after_tool_calling = after_tool_calling or []
        
        # 初始化消息历史
        self.messages = [{"role": "system", "content": system_prompt}]
        if (self.config.response_format and 
            self.config.response_format.get('type') == 'json_object'):
            self.messages += [{"role": "system", "content": "Response in JSON format."}]
        
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
    
    def _setup_logger(self):
        """设置日志记录器"""
        # 创建专用的logger
        self.logger = logging.getLogger(f"llm_session_{self.session_id}")
        self.logger.setLevel(logging.INFO)
        
        # 如果已经有handler，不重复添加
        if self.logger.handlers:
            return
        
        # 创建文件处理器
        log_file = "session.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 创建格式化器
        formatter = logging.Formatter(
            '%(asctime)s [%(name)s] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # 添加处理器
        self.logger.addHandler(file_handler)
    
    def _log_response_data(self, response_data: Dict):
        """记录响应数据到日志文件"""
        if not self.logger:
            return
        
        # 记录基本信息
        self.logger.info("=== LLM Response ===")
        
        # 记录reasoning
        if response_data.get('reasoning'):
            self.logger.info(f"Reasoning: {response_data['reasoning']}")
        
        # 记录content
        if response_data.get('content'):
            self.logger.info(f"Content: {response_data['content']}")
        
        # 记录tool_calls
        if response_data.get('tool_calls'):
            self.logger.info("Tool Calls:")
            for i, tool_call in enumerate(response_data['tool_calls']):
                self.logger.info(f"  Tool #{i+1}:")
                self.logger.info(f"    ID: {tool_call.id}")
                self.logger.info(f"    Function: {tool_call.function.name}")
                self.logger.info(f"    Arguments: {tool_call.function.arguments}")
    
    def _log_tool_result(self, tool_call: 'ToolCall', result: str):
        """记录工具调用结果到日志文件"""
        if not self.logger:
            return
        
        self.logger.info(f"Tool Result for {tool_call.function.name} (ID: {tool_call.id}):")
        self.logger.info(f"  Result: {result}")
        self.logger.info("=" * 50)
    
    def add_user_message(self, content: Union[str, List[Dict]]):
        """
        添加用户消息
        
        Args:
            content: 消息内容，可以是文本字符串或多模态内容列表
                    文本: "hello world"
                    多模态: [
                        {"type": "text", "text": "描述这张图片"},
                        {"type": "image", "image_path": "path/to/image.jpg"}
                    ]
        """
        if isinstance(content, str):
            # 纯文本消息
            self.messages.append({"role": "user", "content": content})
        else:
            # 多模态消息
            self.messages.append({"role": "user", "content": content})
    
    def add_system_message(self, content: str):
        """添加系统消息"""
        self.messages.append({"role": "system", "content": content})
    
    def clear_messages(self):
        """清空消息历史，保留系统提示"""
        self.messages = [{"role": "system", "content": self.system_prompt}]
    
    def _clean_json_content(self, content: str) -> str:
        """清理内容中的markdown代码块标记"""
        # 移除可能的markdown json代码块标记
        content = re.sub(r'^```json\s*', '', content, flags=re.MULTILINE)
        content = re.sub(r'^```\s*$', '', content, flags=re.MULTILINE)
        return content.strip()
    
    def _validate_json_response(self, content: str) -> Tuple[bool, str]:
        """验证JSON格式的响应内容"""
        if not content:
            return False, "空内容"
        
        # 尝试用json5解析（如果可用），否则用标准json
        try:
            if json5:
                json5.loads(content)
            else:
                json.loads(content)
            return True, ""
        except Exception as e:
            return False, f"JSON格式错误: {str(e)}"
    
    def _execute_tool_call(self, tool_call: ToolCall) -> str:
        """执行工具调用"""
        try:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            if function_name in self.tool_functions:
                # 执行前置函数列表
                processed_args = function_args
                for before_func in self.before_tool_calling:
                    processed_args = before_func(function_name, processed_args, self)
                
                # 执行工具函数
                result = self.tool_functions[function_name](**processed_args)
                
                # 执行后置函数列表
                processed_result = result
                for after_func in self.after_tool_calling:
                    processed_result = after_func(processed_result, function_name, self)
                
                # 记录工具调用结果到日志
                result_str = str(processed_result)
                self._log_tool_result(tool_call, result_str)
                
                return result_str
            else:
                error_msg = f"错误: 未找到工具函数 {function_name}"
                self._log_tool_result(tool_call, error_msg)
                return error_msg
                
        except json.JSONDecodeError as e:
            error_msg = f"错误: 参数解析失败 - {str(e)}"
            self._log_tool_result(tool_call, error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"错误: 工具执行失败 - {str(e)}"
            self._log_tool_result(tool_call, error_msg)
            return error_msg
    
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
    
    def call(self, user_message: Union[str, List[Dict]] = None) -> Union[Generator[Any, None, None], Any]:
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
            stream_response = self.client.create_chat_completion(
                model=self.config.model,
                messages=self.messages,
                tools=self.tools_description if self.tools_description else None,
                stream=True,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            
            # 解析流式响应
            response_data = yield from self._parse_streaming_response(stream_response)
            
            # 记录响应数据到日志
            self._log_response_data(response_data)
            
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
                    content = response_data['content']

                    # 如果指定了JSON输出格式，验证JSON格式
                    if (self.config.response_format and 
                        self.config.response_format.get('type') == 'json_object'):
                        # 清理markdown标记
                        content = self._clean_json_content(content)

                        is_valid, error_msg = self._validate_json_response(content)
                        if not is_valid:
                            # JSON格式错误，添加错误信息并继续循环
                            self.messages.append({
                                "role": "assistant",
                                "content": content
                            })
                            self.messages.append({
                                "role": "user",
                                "content": f"输出格式有误，请确保返回有效的JSON格式。错误信息：{error_msg}"
                            })
                            continue
                    
                    self.messages.append({
                        "role": "assistant",
                        "content": content
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
            response = self.client.create_chat_completion(
                model=self.config.model,
                messages=self.messages,
                tools=self.tools_description if self.tools_description else None,
                stream=False,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                response_format=self.config.response_format
            )
            
            final_response = response.choices[0]
            message = final_response.message
            
            # 记录非流式响应数据到日志
            response_data = {
                'content': getattr(message, 'content', ''),
                'reasoning': getattr(message, 'reasoning', ''),
                'tool_calls': []
            }
            
            # 检查是否有工具调用
            if hasattr(message, 'tool_calls') and message.tool_calls:
                # 转换为自定义ToolCall对象
                tool_calls = []
                for tc in message.tool_calls:
                    tool_call_obj = ToolCall()
                    tool_call_obj.id = tc.id
                    tool_call_obj.function.name = tc.function.name
                    tool_call_obj.function.arguments = tc.function.arguments
                    tool_calls.append(tool_call_obj)
                
                # 添加工具调用到响应数据
                response_data['tool_calls'] = tool_calls
                
                # 记录响应数据到日志
                self._log_response_data(response_data)
                
                # 使用统一的工具调用处理逻辑
                tool_executed = self._handle_tool_calls(tool_calls, message.content)
                if tool_executed:
                    continue  # 继续下一轮对话
            else:
                # 没有工具调用，记录响应数据到日志
                self._log_response_data(response_data)
                
                # 添加最终消息并结束
                self.messages.append({
                    "role": "assistant",
                    "content": message.content
                })
                break
        
        return final_response
    
    def dump_messages(self, file_path: Optional[str] = None) -> str:
        """
        将 self.messages 导出到文本文件
        
        Args:
            file_path: 导出文件路径，如果不指定则使用默认路径
                      默认路径: ~/.hq-agent-sdk/messages/{session_id}.json
        
        Returns:
            实际导出的文件路径
        """
        if file_path is None:
            # 使用默认路径
            home_dir = os.path.expanduser("~")
            messages_dir = os.path.join(home_dir, ".hq-agent-sdk", "messages")
            os.makedirs(messages_dir, exist_ok=True)
            file_path = os.path.join(messages_dir, f"{self.session_id}.json")
        
        # 将消息历史写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.messages, f, ensure_ascii=False, indent=2)
        
        return file_path