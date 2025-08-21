# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述
这是一个Python SDK，名为"HQ Agent SDK"，用于LLM会话管理和工具调用。它封装了OpenAI客户端，提供了流式和非流式的LLM交互功能，支持函数工具调用和自动的工具执行循环。

## 核心组件架构

### LLMSession (`llm_session.py`)
- 主要类：管理LLM会话的生命周期
- 支持流式(streaming)和非流式调用
- 内置工具调用执行机制，支持多轮对话
- 消息历史管理，包括用户、助手、系统和工具消息
- 配置类 `AgentConfig`: 模型、温度、最大迭代次数等参数

### 工具Schema转换 (`function_to_tool_schema.py`)
- `function_to_tool_schema()`: 将Python函数转换为OpenAI工具调用格式的JSON Schema
- `python_type_to_schema()`: 处理Python类型注解到JSON Schema的映射
- 支持复杂类型：Union、Optional、Literal、泛型容器等
- docstring解析: 支持 `:param:` 风格的参数描述

### 包入口 (`__init__.py`)
导出主要类和函数：
- `LLMSession`, `AgentConfig`, `ToolCall`
- `function_to_tool_schema`, `python_type_to_schema`

## 常用命令

### 安装和开发
```bash
# 安装包（开发模式）
pip install -e .

# 安装依赖
pip install openai typing_extensions

# 运行示例（如果存在）
python hq_agent_sdk/function_to_tool_schema.py
```

### 构建和分发
```bash
# 构建包
python setup.py sdist bdist_wheel

# 清理构建文件
rm -rf build/ dist/ *.egg-info/
```

## 开发要点

### 依赖关系
- 主要依赖: `openai`, `typing_extensions`  
- Python版本: >=3.8

### 代码结构说明
- 使用dataclass定义配置类
- 流式响应通过Generator实现
- 工具调用采用异步执行模式，支持多轮对话直到无工具调用
- 错误处理集中在工具执行层面

### 工具调用流程
1. 用户消息 -> LLM推理
2. 如果有工具调用：执行工具 -> 添加工具结果到消息历史 -> 继续下一轮
3. 如果无工具调用：结束对话

### 类型系统
该SDK大量使用Python类型注解，`function_to_tool_schema.py`实现了从Python类型到JSON Schema的完整映射，支持现代Python类型系统的大部分特性。