"""
hq-agent-sdk 内部实现可提供给 LLM 的 todos 工具，包含三个主要函数：
# 任务列表 tools
- [x] create_todos：创建 steps list
- [x] update_todos: 更新 steps list 某一项状态
- [x] query_todos: 查询 steps list

通过用户目录下的 ~/.hq-agent-sdk/todos/{UUID}.json 以json格式保存任务列表。
json格式示例如下：
[
  {
    "content": "第一步任务描述",
    "status": "completed"/"in_progress"/"pending",
    "id": "1"
  },
  ...
]
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal


def _get_todos_dir() -> Path:
    """获取todos存储目录路径"""
    home_dir = Path.home()
    todos_dir = home_dir / ".hq-agent-sdk" / "todos"
    todos_dir.mkdir(parents=True, exist_ok=True)
    return todos_dir


def _load_todos_file(session_id: str) -> List[Dict[str, Any]]:
    """加载指定会话的todos文件"""
    todos_dir = _get_todos_dir()
    todos_file = todos_dir / f"{session_id}.json"
    
    if not todos_file.exists():
        return []
    
    try:
        with open(todos_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def _save_todos_file(session_id: str, todos: List[Dict[str, Any]]) -> None:
    """保存todos到文件"""
    todos_dir = _get_todos_dir()
    todos_file = todos_dir / f"{session_id}.json"
    
    with open(todos_file, 'w', encoding='utf-8') as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)


def create_todos(todo_items: List[str], session_id: str = None) -> str:
    """
    创建新的任务列表
    
    :param todo_items: 任务描述列表
    :param session_id: 会话ID，由中间件自动注入
    :return: 创建结果消息
    """
    if not session_id:
        return "错误: session_id 未提供，请确保使用了正确的中间件配置"
    
    todos = []
    for i, content in enumerate(todo_items, 1):
        todos.append({
            "content": content,
            "status": "pending",
            "id": str(i)
        })
    
    _save_todos_file(session_id, todos)
    return f"成功创建任务列表，共 {len(todos)} 个任务"


def update_todos(task_id: str, status: Literal["pending", "in_progress", "completed"], session_id: str = None) -> str:
    """
    更新指定任务的状态
    
    :param task_id: 任务ID
    :param status: 新的任务状态
    :param session_id: 会话ID，由中间件自动注入
    :return: 更新结果消息
    """
    if not session_id:
        return "错误: session_id 未提供，请确保使用了正确的中间件配置"
    
    todos = _load_todos_file(session_id)
    
    if not todos:
        return f"当前会话还没有任务列表，请先创建"
    
    # 查找并更新指定任务
    task_found = False
    old_status = ""
    for todo in todos:
        if todo["id"] == task_id:
            old_status = todo["status"]
            todo["status"] = status
            task_found = True
            break
    
    if not task_found:
        return f"未找到ID为 {task_id} 的任务"
    
    _save_todos_file(session_id, todos)
    return f"成功将任务 {task_id} 状态从 '{old_status}' 更新为 '{status}'"


def query_todos(status_filter: Optional[Literal["pending", "in_progress", "completed"]] = None, session_id: str = None) -> str:
    """
    查询任务列表
    
    :param status_filter: 可选的状态过滤器
    :param session_id: 会话ID，由中间件自动注入
    :return: 任务列表的字符串表示
    """
    if not session_id:
        return "错误: session_id 未提供，请确保使用了正确的中间件配置"
    
    todos = _load_todos_file(session_id)
    
    if not todos:
        return "当前会话还没有任务列表，请先创建"
    
    # 应用状态过滤器
    if status_filter:
        filtered_todos = [todo for todo in todos if todo["status"] == status_filter]
    else:
        filtered_todos = todos
    
    if not filtered_todos:
        filter_msg = f" (状态: {status_filter})" if status_filter else ""
        return f"没有找到符合条件的任务{filter_msg}"
    
    # 格式化输出
    result = "当前任务列表:\n"
    for todo in filtered_todos:
        status_icon = {
            "pending": "⏳",
            "in_progress": "🔄", 
            "completed": "✅"
        }.get(todo["status"], "❓")
        
        result += f"{status_icon} [{todo['id']}] {todo['content']} ({todo['status']})\n"
    
    return result.strip()