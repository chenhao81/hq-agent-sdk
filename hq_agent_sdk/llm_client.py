"""
LLM客户端抽象接口和具体实现
支持OpenAI和Ollama等不同的LLM提供商
"""

import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Generator, Union


class BaseLLMClient(ABC):
    """LLM客户端基类"""
    
    @abstractmethod
    def create_chat_completion(
        self,
        messages: List[Dict],
        model: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[Any, Generator[Any, None, None]]:
        """创建聊天完成"""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI客户端封装"""
    
    def __init__(self, client):
        """
        Args:
            client: OpenAI客户端实例
        """
        self.client = client
    
    def create_chat_completion(
        self,
        messages: List[Dict],
        model: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[Any, Generator[Any, None, None]]:
        """使用OpenAI API创建聊天完成"""
        
        return self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            stream=stream,
            **kwargs
        )


class OllamaClient(BaseLLMClient):
    """Ollama客户端实现"""
    
    def __init__(self, client=None, host: str = "http://localhost:11434"):
        """
        Args:
            client: ollama客户端实例，如果为None则创建新的
            host: Ollama服务器地址
        """
        if client is None:
            try:
                import ollama
                self.client = ollama.Client(host=host)
            except ImportError:
                raise ImportError("请安装ollama库: pip install ollama")
        else:
            self.client = client
    
    def _convert_messages_to_ollama(self, messages: List[Dict]) -> List[Dict]:
        """将标准消息格式转换为Ollama格式"""
        ollama_messages = []
        
        for msg in messages:
            # 基本消息转换
            ollama_msg = {
                "role": msg["role"],
                "content": msg.get("content", "")
            }
            
            # 处理多模态消息（包含图像）
            if isinstance(msg.get("content"), list):
                # 多模态消息处理
                text_content = ""
                images = []
                
                for item in msg["content"]:
                    if item.get("type") == "text":
                        text_content += item.get("text", "")
                    elif item.get("type") == "image":
                        # 处理图像路径
                        image_path = item.get("image_path")
                        if image_path:
                            try:
                                import base64
                                with open(image_path, "rb") as image_file:
                                    encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
                                    images.append(encoded_image)
                            except Exception as e:
                                text_content += f"[图像加载失败: {str(e)}]"
                
                ollama_msg["content"] = text_content
                if images:
                    ollama_msg["images"] = images
            
            # 处理工具调用消息（OpenAI格式 -> Ollama格式）
            elif msg.get("tool_calls"):
                # 助手调用工具的消息
                tool_calls_text = ""
                for tc in msg["tool_calls"]:
                    tool_calls_text += f"调用工具: {tc['function']['name']}\n"
                    tool_calls_text += f"参数: {tc['function']['arguments']}\n"
                content = msg.get("content") or ""
                ollama_msg["content"] = (content + "\n" + tool_calls_text).strip()
            
            # 处理工具结果消息
            elif msg["role"] == "tool":
                ollama_msg["role"] = "user"  # Ollama将工具结果作为用户消息
                ollama_msg["content"] = f"工具执行结果: {msg['content']}"
            
            ollama_messages.append(ollama_msg)
        
        return ollama_messages
    
    def _add_tools_to_system_message(self, messages: List[Dict], tools: Optional[List[Dict]]) -> List[Dict]:
        """将工具描述添加到系统消息中"""
        if not tools:
            return messages
        
        tools_prompt = "\n\n你可以使用以下工具：\n"
        for tool in tools:
            func_info = tool.get("function", {})
            tools_prompt += f"- {func_info.get('name', '')}: {func_info.get('description', '')}\n"
            
            # 添加参数信息
            params = func_info.get("parameters", {}).get("properties", {})
            if params:
                tools_prompt += "  参数：\n"
                for param_name, param_info in params.items():
                    tools_prompt += f"    - {param_name}: {param_info.get('description', '')}\n"
        
        tools_prompt += "\n如需调用工具，请按以下格式回复：\n"
        tools_prompt += "调用工具: [工具名称]\n参数: [JSON格式的参数]\n"
        
        # 查找系统消息并添加工具信息
        modified_messages = []
        system_msg_found = False
        
        for msg in messages:
            if msg["role"] == "system" and not system_msg_found:
                modified_msg = msg.copy()
                modified_msg["content"] += tools_prompt
                modified_messages.append(modified_msg)
                system_msg_found = True
            else:
                modified_messages.append(msg)
        
        # 如果没有系统消息，创建一个
        if not system_msg_found:
            modified_messages.insert(0, {
                "role": "system",
                "content": "你是一个AI助手。" + tools_prompt
            })
        
        return modified_messages
    
    def _parse_tool_calls_from_content(self, content: str) -> Optional[List[Dict]]:
        """从回复内容中解析工具调用"""
        if not content or "调用工具:" not in content or "参数:" not in content:
            return None
        
        try:
            lines = content.split('\n')
            tool_name = None
            tool_args = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('调用工具:'):
                    tool_name = line.replace('调用工具:', '').strip()
                elif line.startswith('参数:'):
                    tool_args = line.replace('参数:', '').strip()
            
            if tool_name and tool_args:
                # 验证JSON格式
                json.loads(tool_args)
                
                tool_call = {
                    "id": f"call_{hash(tool_name + tool_args) % 100000}",
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": tool_args
                    }
                }
                return [tool_call]
                
        except (json.JSONDecodeError, Exception):
            pass
        
        return None
    
    def create_chat_completion(
        self,
        messages: List[Dict],
        model: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[Any, Generator[Any, None, None]]:
        """使用Ollama API创建聊天完成"""
        
        # 转换消息格式
        ollama_messages = self._convert_messages_to_ollama(messages)
        
        # 添加工具信息到系统消息
        if tools:
            ollama_messages = self._add_tools_to_system_message(ollama_messages, tools)
        
        # 构建选项
        options = {
            "temperature": temperature,
        }
        if max_tokens:
            options["num_predict"] = max_tokens
        
        # 调用ollama
        try:
            response = self.client.chat(
                model=model,
                messages=ollama_messages,
                stream=stream,
                options=options,
                **kwargs
            )
            
            if stream:
                return self._handle_streaming_response(response)
            else:
                return self._handle_non_streaming_response(response, tools is not None)
                
        except Exception as e:
            raise Exception(f"Ollama调用失败: {str(e)}")
    
    def _handle_streaming_response(self, response) -> Generator[Any, None, None]:
        """处理流式响应"""
        for chunk in response:
            # 转换为类似OpenAI的格式
            delta = type('Delta', (), {})()
            delta.content = chunk.get('message', {}).get('content', '')
            delta.tool_calls = None
            delta.reasoning = None
            
            # 包装成类似OpenAI的chunk格式
            mock_chunk = type('Chunk', (), {})()
            mock_chunk.choices = [type('Choice', (), {'delta': delta})()]
            
            yield mock_chunk
    
    def _handle_non_streaming_response(self, response, has_tools: bool = False):
        """处理非流式响应"""
        # 创建类似OpenAI的响应格式
        content = response.get('message', {}).get('content', '')
        
        # 构建消息对象
        message = type('Message', (), {})()
        message.content = content
        message.tool_calls = None
        
        # 如果有工具，尝试解析工具调用
        if has_tools:
            tool_calls = self._parse_tool_calls_from_content(content)
            if tool_calls:
                # 转换为OpenAI格式的工具调用
                openai_tool_calls = []
                for tc in tool_calls:
                    tool_call = type('ToolCall', (), {})()
                    tool_call.id = tc['id']
                    tool_call.type = tc['type']
                    tool_call.function = type('Function', (), {})()
                    tool_call.function.name = tc['function']['name']
                    tool_call.function.arguments = tc['function']['arguments']
                    openai_tool_calls.append(tool_call)
                
                message.tool_calls = openai_tool_calls
                message.content = None  # 工具调用时清空内容
        
        # 构建选择对象
        choice = type('Choice', (), {})()
        choice.message = message
        choice.finish_reason = 'stop'
        
        # 构建响应对象
        mock_response = type('Response', (), {})()
        mock_response.choices = [choice]
        mock_response.model = response.get('model', '')
        
        return mock_response


