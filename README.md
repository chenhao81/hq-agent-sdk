# HQ Agent SDK

为了快速入手 Agent 制作，在简单场景里又不喜欢 Langchain 那种过于抽象的架构和封装。所以自制了一个简单框架。

一个简洁的Python SDK，专为LLM会话管理和工具调用而设计。HQ Agent SDK封装了OpenAI客户端，提供流式和非流式的LLM交互功能，支持函数工具调用和自动的工具执行循环。

## 🚀 特性

- **智能会话管理**: 完整的LLM会话生命周期管理，自动生成唯一session_id
- **工具调用支持**: 自动执行工具调用，支持多轮对话
- **流式响应**: 支持流式和非流式两种调用模式
- **多LLM提供商**: 统一接口支持OpenAI、Ollama等多种LLM提供商
- **中间件系统**: 专业的中间件架构，支持工具调用的前置和后置处理
- **内置Todos工具**: 提供任务管理功能，支持任务创建、更新和查询
- **类型安全**: 完整的Python类型注解支持
- **Schema自动转换**: 自动将Python函数转换为OpenAI工具调用格式
- **消息历史**: 自动管理用户、助手、系统和工具消息历史

## 📦 安装

```bash
pip install -e .
```

### 依赖要求

- Python >= 3.8
- openai
- typing_extensions
- ollama（可选，用于本地LLM支持）

## 🛠️ 快速开始

### 基本使用

```python
from openai import OpenAI
from hq_agent_sdk import LLMSession, AgentConfig

# 创建OpenAI客户端
client = OpenAI(api_key="your-api-key")

# 配置Agent
config = AgentConfig(
    model="gpt-4",
    temperature=0.7,
    max_iterations=5
)

# 创建会话
session = LLMSession(client=client, config=config, stream=False)

# 发送消息
response = session.call("你好，请帮我写一个Python函数")
print(response.message.content)
```

### 工具调用示例

```python
from openai import OpenAI
from hq_agent_sdk import LLMSession, AgentConfig, function_to_tool_schema

# 定义工具函数
def get_weather(city: str) -> str:
    """获取指定城市的天气信息
    
    :param city: 城市名称
    :return: 天气描述
    """
    return f"{city}的天气是晴天，气温25°C"

# 创建OpenAI客户端
client = OpenAI(api_key="your-api-key")

# 配置和创建会话
config = AgentConfig(model="gpt-4")
session = LLMSession(
    client=client, 
    tools=[get_weather],  # 直接传入工具函数列表
    config=config, 
    stream=False
)

# 发送需要工具调用的消息
response = session.call("北京今天天气怎么样？")
print(response.message.content)
```

### 流式响应

```python
from openai import OpenAI
from hq_agent_sdk import LLMSession, AgentConfig

# 创建OpenAI客户端
client = OpenAI(api_key="your-api-key")

# 配置
config = AgentConfig(model="gpt-4")
session = LLMSession(client=client, config=config, stream=True)  # 启用流式响应

# 流式获取响应
for delta in session.call("请写一首关于AI的诗"):
    if hasattr(delta, 'content') and delta.content:
        print(delta.content, end="", flush=True)
```

### 内置Todos工具

```python
from hq_agent_sdk import LLMSession, OpenAIClient, create_todos, update_todos, query_todos

# 创建会话，自动包含todos中间件
session = LLMSession(
    client=OpenAIClient(api_key="your-key"),
    tools=[create_todos, update_todos, query_todos]  
)

# LLM可以直接调用todos工具，无需提供session_id
# 例如LLM调用：create_todos(["实现用户登录", "编写单元测试", "部署到生产环境"])
# 中间件会自动注入session_id参数
```

### 多LLM提供商支持

```python
from hq_agent_sdk import LLMSession, OpenAIClient, OllamaClient

# 使用OpenAI
openai_session = LLMSession(
    client=OpenAIClient(api_key="your-key", base_url="https://api.openai.com/v1"),
    tools=[your_tools]
)

# 使用Ollama本地LLM
ollama_session = LLMSession(
    client=OllamaClient(base_url="http://localhost:11434"),
    tools=[your_tools]
)
```

### 工具前后回调函数

```python
def tools_before_hook(tool_name: str, args: dict, session) -> dict:
    """工具调用前的回调函数"""
    print(f"- {tool_name}({','.join(f'{k}={v}' for k, v in args.items())})")
    return args

def tools_after_hook(result, tool_name: str, session):
    """工具调用后的回调函数"""
    print(f"⎿ {result}")
    return result

# 在LLMSession中使用回调函数
session = LLMSession(
    client=client,
    tools=[get_weather, calculate],
    config=AgentConfig(model="gpt-4", temperature=0.1),
    before_tool_calling=[tools_before_hook],  # 前置回调函数列表
    after_tool_calling=[tools_after_hook]     # 后置回调函数列表
)

# 这样每次工具调用时都会自动执行回调函数
response = session.call("北京今天天气怎么样？然后帮我计算 15 * 23")
```

### 自定义中间件

```python
from hq_agent_sdk import ToolMiddleware, LLMSession

class LoggingMiddleware(ToolMiddleware):
    def before_tool_call(self, tool_name: str, args: dict, session) -> dict:
        print(f"调用工具: {tool_name}, 参数: {args}")
        return args
    
    def after_tool_call(self, result, tool_name: str, session):
        print(f"工具 {tool_name} 执行完成，结果: {result}")
        return result

# 添加自定义中间件
session = LLMSession(client=client, auto_add_todos_middleware=False)
session.middleware_manager.add_middleware(LoggingMiddleware())
```

## 📚 核心组件

### LLMSession

主要的会话管理类，负责：
- LLM调用的封装
- 消息历史管理
- 工具调用的自动执行
- 流式和非流式响应处理

### AgentConfig

配置类，包含：
- `model`: 使用的模型名称（默认："gpt-oss:20b"）
- `temperature`: 温度参数（默认：0.1）
- `max_iterations`: 最大迭代次数（默认：5）
- `max_tokens`: 最大Token数（可选）
- `timeout`: 超时时间（默认：30.0秒）

### 工具Schema转换

- `function_to_tool_schema()`: 将Python函数转换为OpenAI工具调用格式
- `python_type_to_schema()`: Python类型到JSON Schema的映射
- 支持复杂类型：Union、Optional、Literal、泛型容器等

## 🔧 高级功能

### 自定义工具

```python
from typing import Union, Optional

def calculate(expression: str, precision: Optional[int] = 2) -> Union[float, str]:
    """计算数学表达式
    
    :param expression: 数学表达式字符串
    :param precision: 计算精度，默认2位小数
    :return: 计算结果或错误信息
    """
    try:
        result = eval(expression)
        return round(result, precision)
    except:
        return "计算错误"

# 自动生成工具Schema
tool_schema = function_to_tool_schema(calculate)
```

### 消息历史管理

```python
# 获取消息历史
history = session.messages

# 清空历史
session.clear_messages()

# 添加系统消息
session.add_system_message("你是一个专业的Python开发助手")

# 添加用户消息
session.add_user_message("请帮我解释这段代码")
```

## 🏗️ 架构说明

```
hq_agent_sdk/
├── __init__.py              # 包入口，导出主要类和函数
├── llm_session.py           # 核心会话管理类
├── llm_client.py            # LLM客户端抽象层
├── middleware.py            # 中间件系统
├── function_to_tool_schema.py  # 工具Schema转换模块
└── tools/
    └── todos.py             # 内置todos任务管理工具
```

### 工具调用流程

1. 用户消息 → LLM推理
2. 如果有工具调用：执行工具 → 添加工具结果到消息历史 → 继续下一轮
3. 如果无工具调用：结束对话

## 🤝 开发指南

### 本地开发

```bash
# 克隆项目
git clone <your-repo-url>
cd hq-agent-sdk

# 安装开发依赖
pip install -e .

# 运行示例
python hq_agent_sdk/function_to_tool_schema.py
```

### 构建和分发

```bash
# 构建包
python setup.py sdist bdist_wheel

# 清理构建文件
rm -rf build/ dist/ *.egg-info/
```

## 📝 版本历史

### v0.0.3
- 简化了工具调用中间件的设计，改成输入函数列表
BUGS:
- 因为 Ollama 输出格式和 openAI不一样，处理起来还挺麻烦，没做好，暂时用 openAI接口客户端

### v0.0.2
- **新增多LLM提供商支持**: OpenAI、Ollama统一接口
- **中间件系统**: 专业的中间件架构，支持工具调用前置和后置处理
- **内置Todos工具**: 提供完整的任务管理功能，支持会话级别的任务隔离
- **会话管理增强**: 自动生成唯一session_id，支持多会话并发
- **架构重构**: 清晰的分层设计，更好的代码组织

### v0.0.1
- 初始版本发布
- 基础LLM会话管理功能
- 工具调用支持
- Schema自动转换

## 📄 许可证

MIT License

## 🔗 相关链接

- [OpenAI API 文档](https://platform.openai.com/docs)
- [JSON Schema 规范](https://json-schema.org/)

---

**HQ Agent SDK** - 让LLM工具调用变得简单而强大！