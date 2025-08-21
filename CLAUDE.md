# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述
这是一个Python SDK，名为"HQ Agent SDK"，用于LLM会话管理和工具调用。它提供统一的接口支持多种LLM提供商（OpenAI、Ollama等），具备流式和非流式的LLM交互功能，支持函数工具调用和自动的工具执行循环。

## 核心组件架构

### LLMSession (`llm_session.py`)
- 主要类：管理LLM会话的生命周期
- 支持流式(streaming)和非流式调用
- 内置工具调用执行机制，支持多轮对话
- 消息历史管理，包括用户、助手、系统和工具消息
- 配置类 `AgentConfig`: 模型、温度、最大迭代次数等参数
- **会话管理**: 自动生成唯一的 `session_id`，用于标识和隔离不同会话
- **中间件集成**: 内置中间件管理器，支持工具调用的前置和后置处理

### 中间件系统 (`middleware.py`)
- `ToolMiddleware`: 抽象基类，定义工具调用中间件接口
- `TodosMiddleware`: 专用中间件，为todos工具自动注入session_id
- `MiddlewareManager`: 中间件管理器，支持多个中间件的链式处理
- **设计优势**: 保持框架核心代码纯净，通过中间件处理特定工具的上下文需求

### Todos工具系统 (`tools/todos.py`)
- `create_todos()`: 创建任务列表，支持批量添加任务
- `update_todos()`: 更新任务状态（pending/in_progress/completed）
- `query_todos()`: 查询任务列表，支持状态过滤
- **文件存储**: 任务保存在 `~/.hq-agent-sdk/todos/{session_id}.json`
- **会话隔离**: 每个LLMSession实例拥有独立的任务列表

### LLM客户端抽象 (`llm_client.py`)
- `BaseLLMClient`: 抽象基类，定义统一的LLM调用接口
- `OpenAIClient`: OpenAI API的封装实现
- `OllamaClient`: Ollama的封装实现，支持本地部署的开源模型
- 统一的接口设计，便于切换不同的LLM提供商

### 工具Schema转换 (`function_to_tool_schema.py`)
- `function_to_tool_schema()`: 将Python函数转换为OpenAI工具调用格式的JSON Schema
- `python_type_to_schema()`: 处理Python类型注解到JSON Schema的映射
- 支持复杂类型：Union、Optional、Literal、泛型容器等
- docstring解析: 支持 `:param:` 风格的参数描述

### 包入口 (`__init__.py`)
导出主要类和函数：
- `LLMSession`, `AgentConfig`, `ToolCall`
- `function_to_tool_schema`, `python_type_to_schema`
- `BaseLLMClient`, `OpenAIClient`, `OllamaClient`
- `ToolMiddleware`, `TodosMiddleware`, `MiddlewareManager`
- `create_todos`, `update_todos`, `query_todos`

## 常用命令

### 安装和开发
```bash
# 安装包（开发模式）
pip install -e .

# 安装依赖
pip install openai typing_extensions ollama

# 运行使用示例
python example_usage.py
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
- 主要依赖: `openai`, `typing_extensions`, `ollama`
- Python版本: >=3.8

### 多LLM提供商支持
- **OpenAI**: 通过官方openai库支持GPT系列模型
- **Ollama**: 通过ollama库支持本地部署的开源模型（Llama、Mistral等）
- 统一的接口设计，切换LLM提供商只需更换客户端对象

### 代码结构说明
- 使用dataclass定义配置类
- 流式响应通过Generator实现
- 工具调用采用异步执行模式，支持多轮对话直到无工具调用
- 错误处理集中在工具执行层面

### 工具调用流程
1. 用户消息 -> LLM推理
2. 如果有工具调用：执行工具 -> 添加工具结果到消息历史 -> 继续下一轮
3. 如果无工具调用：结束对话

### 中间件系统架构
- **关注点分离**: 中间件处理工具调用的横切关注点，如参数注入、日志记录、权限验证等
- **链式处理**: 支持多个中间件按顺序执行，before_tool_call正序，after_tool_call逆序
- **零侵入**: 工具函数无需修改即可享受中间件功能
- **可扩展**: 可轻松添加自定义中间件处理不同场景需求

### Todos工具使用说明
**LLM调用方式（推荐）:**
```python
# 创建任务列表
create_todos(["实现登录功能", "写单元测试", "更新文档"])

# 更新任务状态
update_todos("1", "in_progress")  # 开始第一个任务
update_todos("1", "completed")    # 完成第一个任务

# 查询任务
query_todos()                     # 查询所有任务
query_todos("pending")           # 只查询待处理任务
```

**直接调用方式（需要手动提供session_id）:**
```python
session_id = "your-session-id"
create_todos(["任务1", "任务2"], session_id=session_id)
```

### 类型系统
该SDK大量使用Python类型注解，`function_to_tool_schema.py`实现了从Python类型到JSON Schema的完整映射，支持现代Python类型系统的大部分特性。