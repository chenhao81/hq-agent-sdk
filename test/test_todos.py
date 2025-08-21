#!/usr/bin/env python3
"""
测试使用Ollama qwen2.5vl:7b模型创建todos列表的示例

运行前请确保：
1. 已安装Ollama：curl -fsSL https://ollama.com/install.sh | sh
2. 已下载qwen2.5vl:7b模型：ollama pull qwen2.5vl:7b
3. Ollama服务正在运行：ollama serve
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from hq_agent_sdk import LLMSession, OpenAIClient, AgentConfig
from hq_agent_sdk import create_todos, update_todos, query_todos
from openai import OpenAI

def main():
    """使用 OpenAI gpt-oss:20b 模型测试todos功能"""
    
    print("🚀 启动 OpenAI gpt-oss:20b 模型测试todos功能...")
    
    # 创建Ollama客户端
    client = OpenAIClient(
         OpenAI(
            base_url="http://192.168.1.16:11434/v1",
            api_key="EMPTY"
        )
    )
    
    # 配置参数
    config = AgentConfig(
        model="gpt-oss:20b",
        temperature=0.7,
        max_iterations=5
    )
    
    # 创建LLM会话，包含todos工具
    session = LLMSession(
        client=client,
        config=config,
        tools=[create_todos, update_todos, query_todos],
        stream=False,
        system_prompt="""你是一个项目管理助手。你可以帮助用户创建和管理任务列表。
请根据用户的需求合理使用这些工具。"""
    )
    
    print(f"✅ 成功创建会话，Session ID: {session.session_id}")
    
    # 测试场景1：让AI创建一个软件开发项目的todos列表
    print("\n" + "="*60)
    print("📋 测试场景1: 创建软件开发项目任务列表")
    print("="*60)
    
    user_message = """请帮我创建一个Web应用开发项目的任务列表，包括：
1. 需求分析和设计
2. 前端开发
3. 后端API开发  
4. 数据库设计
5. 测试和部署
6. 文档编写"""
    
    print(f"用户: {user_message}")
    print("\n🤖 AI回复:")
    
    response = session.call(user_message)
    print(response.message.content)
    
    # 测试场景2：查询创建的任务列表
    print("\n" + "="*60)
    print("🔍 测试场景2: 查询所有任务")
    print("="*60)
    
    query_message = "请显示所有任务的当前状态"
    print(f"用户: {query_message}")
    print("\n🤖 AI回复:")
    
    response = session.call(query_message)
    print(response.message.content)
    
    # 测试场景3：更新任务状态
    print("\n" + "="*60)
    print("⏳ 测试场景3: 更新任务状态")
    print("="*60)
    
    update_message = "请将第一个任务标记为进行中，第二个任务标记为已完成"
    print(f"用户: {update_message}")
    print("\n🤖 AI回复:")
    
    response = session.call(update_message)
    print(response.message.content)


    # 测试场景2：查询创建的任务列表
    print("\n" + "="*60)
    print("🔍 测试场景3.1: 查询所有任务")
    print("="*60)
    
    query_message = "请显示所有任务的当前状态"
    print(f"用户: {query_message}")
    print("\n🤖 AI回复:")
    
    response = session.call(query_message)
    print(response.message.content)
    
    # 测试场景4：查询特定状态的任务
    print("\n" + "="*60)
    print("🎯 测试场景4: 查询进行中的任务")
    print("="*60)
    
    filter_message = "请只显示状态为'进行中'的任务"
    print(f"用户: {filter_message}")
    print("\n🤖 AI回复:")
    
    response = session.call(filter_message)
    print(response.message.content)
    
    print("\n" + "="*60)
    print("✅ 测试完成！")
    print("="*60)
    print(f"📊 会话统计:")
    print(f"  - Session ID: {session.session_id}")
    print(f"  - 消息数量: {len(session.messages)}")
    print(f"  - 模型: {config.model}")
        

if __name__ == "__main__":
    main()