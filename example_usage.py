"""
HQ Agent SDK 使用示例
展示如何使用OpenAI和Ollama客户端
"""

from hq_agent_sdk import LLMSession, AgentConfig, OpenAIClient, OllamaClient


def get_weather(city: str) -> str:
    """
    获取城市天气信息
    
    :param city: 城市名称
    """
    # 模拟天气API
    weather_data = {
        "北京": "晴天，20°C",
        "上海": "多云，18°C", 
        "广州": "小雨，25°C"
    }
    return weather_data.get(city, f"{city}的天气信息暂不可用")


def calculate(expression: str) -> float:
    """
    计算数学表达式
    
    :param expression: 数学表达式字符串
    """
    try:
        # 注意：实际使用时应该使用更安全的表达式计算方法
        result = eval(expression)
        return result
    except Exception as e:
        return f"计算错误: {str(e)}"


def example_openai():
    """使用OpenAI的示例"""
    print("=== OpenAI示例 ===")
    
    # 创建OpenAI客户端 (需要先安装openai库并配置API key)
    try:
        from openai import OpenAI
        openai_raw_client = OpenAI(api_key="your-openai-api-key")
        client = OpenAIClient(openai_raw_client)
        
        # 配置
        config = AgentConfig(
            model="gpt-3.5-turbo",
            max_iterations=3,
            temperature=0.1
        )
        
        # 创建会话
        session = LLMSession(
            client=client,
            tools=[get_weather, calculate],
            config=config,
            stream=False,
            system_prompt="你是一个helpful的AI助手，可以查询天气和计算数学表达式。"
        )
        
        # 对话
        response = session.call("北京今天天气怎么样？")
        print("AI回复:", response.message.content)
        
        # 继续对话
        response = session.call("帮我计算 15 * 23 + 7")
        print("AI回复:", response.message.content)
        
    except ImportError:
        print("需要安装openai库: pip install openai")
    except Exception as e:
        print(f"OpenAI示例运行失败: {str(e)}")


def example_ollama():
    """使用Ollama的示例"""
    print("\n=== Ollama示例 ===")
    
    try:
        # 创建Ollama客户端
        client = OllamaClient(host="http://192.168.56.1:11434")
        
        # 配置
        config = AgentConfig(
            model="qwen2.5vl:7b",  # 使用Ollama中的模型
            max_iterations=3,
            temperature=0.1
        )
        
        # 创建会话
        session = LLMSession(
            client=client,
            tools=[get_weather, calculate],
            config=config,
            stream=False,
            system_prompt="你是一个helpful的AI助手，可以查询天气和计算数学表达式。"
        )
        
        # 对话
        response = session.call("上海今天天气怎么样？")
        print("AI回复:", response.message.content)
        
        # 继续对话
        response = session.call("帮我计算 100 - 25 * 2")
        print("AI回复:", response.message.content)
        
    except Exception as e:
        print(f"Ollama示例运行失败: {str(e)}")
        print("请确保:")
        print("1. Ollama服务正在运行 (ollama serve)")
        print("2. 已下载相应的模型 (ollama pull llama3.1:8b)")
        print("3. 安装了ollama库 (pip install ollama)")


def example_streaming():
    """流式输出示例"""
    print("\n=== 流式输出示例 (Ollama) ===")
    
    try:
        client = OllamaClient(host="http://192.168.56.1:11434")
        
        config = AgentConfig(
            model="qwen2.5vl:7b",
            max_iterations=2,
            temperature=0.7
        )
        
        session = LLMSession(
            client=client,
            tools=[],  # 不使用工具，纯对话
            config=config,
            stream=True,
            system_prompt="你是一个友好的AI助手。"
        )
        
        print("流式输出:")
        for delta in session.call("请介绍一下Python编程语言的特点"):
            if hasattr(delta, 'content') and delta.content:
                print(delta.content, end='', flush=True)
        
        print("\n")
        
    except Exception as e:
        print(f"流式输出示例失败: {str(e)}")


def example_multimodal_vision():
    """多模态视觉示例（使用Ollama的视觉模型）"""
    print("\n=== 多模态视觉示例 (Ollama qwen2.5vl:7b) ===")
    
    try:
        # 创建Ollama客户端
        client = OllamaClient(host="http://192.168.56.1:11434")
        
        # 配置，使用支持视觉的模型
        config = AgentConfig(
            model="qwen2.5vl:7b",  # 使用Qwen2.5 Vision Language模型
            max_iterations=2,
            temperature=0.1
        )
        
        # 创建会话
        session = LLMSession(
            client=client,
            tools=[],  # 不使用工具，专注于图像理解
            config=config,
            stream=False,
            system_prompt="你是一个专业的图像分析助手，能够详细描述和分析图像内容。"
        )
        
        # 构建多模态消息（文本 + 图像）
        multimodal_message = [
            {"type": "text", "text": "请详细描述这张图片的内容，包括场景、物体、颜色等细节。"},
            {"type": "image", "image_path": "res/img.png"}
        ]
        
        print("正在分析图片...")
        response = session.call(multimodal_message)
        print("AI分析结果:")
        print(response.message.content)
        
        # 继续对话，询问更多细节
        follow_up_message = [
            {"type": "text", "text": "图片中有什么特别有趣或引人注目的地方吗？"}
        ]
        
        response = session.call(follow_up_message)
        print("\nAI补充分析:")
        print(response.message.content)
        
    except Exception as e:
        print(f"多模态视觉示例失败: {str(e)}")
        print("请确保:")
        print("1. Ollama服务正在运行 (ollama serve)")
        print("2. 已下载qwen2.5vl:7b模型 (ollama pull qwen2.5vl:7b)")
        print("3. res/img.png文件存在")
        print("4. 安装了ollama库 (pip install ollama)")


if __name__ == "__main__":
    print("HQ Agent SDK 使用示例")
    print("\n使用说明:")
    print("1. OpenAI: 需要设置API key环境变量或直接传入")
    print("2. Ollama: 需要本地运行Ollama服务和下载模型")
    print("3. 工具调用: 函数会自动转换为工具调用格式")
    print("4. 流式输出: 支持实时输出，提升用户体验")
    print("5. 多模态: 支持图像+文本输入")
    print("例子代码使用Ollama本地运行开源千问视觉模型(qwen2.5vl:7b)")
    print("====================")
    
    # 运行示例
    # example_openai()
    example_ollama()
    example_streaming()
    # example_multimodal_vision()
    
