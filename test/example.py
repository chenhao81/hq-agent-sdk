"""
Runner 类使用示例
展示如何使用不同的 Runner 来自定义 LLMSession 的输出处理
"""
from typing import List, Dict, Any, Optional, Literal, Union

from hq_agent_sdk import (
    LLMSession, AgentConfig, OpenAIClient, OllamaClient,
    DefaultRunner
)


def get_weather(city: str) -> str:
    """
    获取城市天气信息
    
    :param city: 城市名称
    """
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
        result = eval(expression)
        return result
    except Exception as e:
        return f"计算错误: {str(e)}"


# Hook函数，用于轻量化的LLMSession before/after函数列表
def tools_before_hook(tool_name: str, args: Dict[str, Any], session) -> Dict[str, Any]:
    """
    显示工具调用
    """
    print(f"- {tool_name}({','.join(f'{k}={v}' for k, v in args.items())})")
    return args


def tools_after_hook(result: Any, tool_name: str, session) -> Any:
    """
    显示工具调用结果
    """
    print(f"⎿ {result}")
    return result

def demo_default_runner():
    """演示默认 Runner"""
    print("\n=== 默认 Runner 示例 ===")
    
    # 创建客户端（这里使用模拟的配置）
    from openai import OpenAI
    openai_raw_client = OpenAI(
        base_url="http://192.168.1.16:11434/v1",
        api_key="EMPTY"
    )
    client = OpenAIClient(openai_raw_client)
    
    # 创建会话（流式）
    session = LLMSession(
        client=client,
        tools=[get_weather, calculate],
        config=AgentConfig(model="gpt-oss:20b", temperature=0.1),
        stream=True,
        system_prompt="你是一个helpful的AI助手。",
        before_tool_calling=[tools_before_hook],
        after_tool_calling=[tools_after_hook]
    )
    
    # 使用默认Runner
    runner = DefaultRunner(session)
    runner.run("北京今天天气怎么样？然后帮我计算 15 * 23")
        


def demo_non_streaming():
    """演示非流式 Runner"""
    print("\n=== 非流式 Runner 示例 ===")
    
    try:
        from openai import OpenAI
        openai_raw_client = OpenAI(
            base_url="http://192.168.1.16:11434/v1",
            api_key="EMPTY"
        )
        client = OpenAIClient(openai_raw_client)
        
        # 创建非流式会话
        session = LLMSession(
            client=client,
            tools=[get_weather],
            config=AgentConfig(model="gpt-oss:20b"),
            stream=False  # 关键：设为非流式
        )
        
        # 任何Runner都支持非流式
        runner = DefaultRunner(session)
        result = runner.run("北京天气怎么样？")
        
    except Exception as e:
        print(f"演示失败: {e}")


if __name__ == "__main__":
    print("Runner 类使用示例")
    print("注意: 需要配置正确的LLM服务端点才能运行")
    
    # 运行各种演示
    demo_default_runner()
    demo_non_streaming()
    
    print("\n演示完成! 🎉")