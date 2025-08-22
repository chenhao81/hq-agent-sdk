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
from typing import List, Dict, Any, Optional, Literal, Union



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


def create_todos(todo_items: List[str], session_id: str = "default") -> Dict[str, Any]:
    """
    创建新的任务列表
    
    :param todo_items: 任务描述列表
    :param session_id: 会话ID，如果未提供则使用默认值
    :return: 包含success、msg、data字段的字典
    """
    if not session_id:
        session_id = "default"
    
    todos = []
    for i, content in enumerate(todo_items, 1):
        todos.append({
            "content": content,
            "status": "pending",
            "id": str(i)
        })
    
    _save_todos_file(session_id, todos)
    return {
        "success": True,
        "msg": f"成功创建任务列表，共 {len(todos)} 个任务",
        "data": todos
    }


def update_todos(task_id: str, status: Literal["pending", "in_progress", "completed"], session_id: str = "default") -> Dict[str, Any]:
    """
    更新指定任务的状态
    
    :param task_id: 任务ID
    :param status: 新的任务状态
    :param session_id: 会话ID，如果未提供则使用默认值
    :return: 包含success、msg、data字段的字典
    """
    if not session_id:
        session_id = "default"
    
    # 验证状态参数
    valid_statuses = ["pending", "in_progress", "completed"]
    if status not in valid_statuses:
        return {
            "success": False,
            "msg": f"无效的状态值: '{status}'。有效状态为: {', '.join(valid_statuses)}",
            "data": None
        }
    
    todos = _load_todos_file(session_id)
    
    if not todos:
        return {
            "success": False,
            "msg": "当前会话还没有任务列表，请先创建",
            "data": None
        }
    
    # 查找并更新指定任务
    task_found = False
    old_status = ""
    updated_task = None
    for todo in todos:
        if todo["id"] == task_id:
            old_status = todo["status"]
            todo["status"] = status
            updated_task = todo.copy()
            task_found = True
            break
    
    if not task_found:
        return {
            "success": False,
            "msg": f"未找到ID为 {task_id} 的任务",
            "data": None
        }
    
    _save_todos_file(session_id, todos)
    return {
        "success": True,
        "msg": f"成功将任务 {task_id} 状态从 '{old_status}' 更新为 '{status}'",
        "data": {
            "updated_task": updated_task,
            "old_status": old_status,
            "new_status": status
        }
    }


def query_todos(status_filter: Optional[Literal["pending", "in_progress", "completed"]] = None, session_id: str = "default") -> Dict[str, Any]:
    """
    查询任务列表
    
    :param status_filter: 可选的状态过滤器
    :param session_id: 会话ID，如果未提供则使用默认值
    :return: 包含success、msg、data字段的字典
    """
    if not session_id:
        session_id = "default"
    
    # 验证状态过滤器参数
    if status_filter is not None:
        valid_statuses = ["pending", "in_progress", "completed"]
        if status_filter not in valid_statuses:
            return {
                "success": False,
                "msg": f"无效的状态过滤器: '{status_filter}'。有效状态为: {', '.join(valid_statuses)}",
                "data": None
            }
    
    todos = _load_todos_file(session_id)
    
    if not todos:
        return {
            "success": False,
            "msg": "当前会话还没有任务列表，请先创建",
            "data": None
        }
    
    # 应用状态过滤器
    if status_filter:
        filtered_todos = [todo for todo in todos if todo["status"] == status_filter]
    else:
        filtered_todos = todos
    
    if not filtered_todos:
        filter_msg = f" (状态: {status_filter})" if status_filter else ""
        return {
            "success": False,
            "msg": f"没有找到符合条件的任务{filter_msg}",
            "data": []
        }
    
    return {
        "success": True,
        "msg": f"查询到 {len(filtered_todos)} 个任务" + (f" (状态: {status_filter})" if status_filter else ""),
        "data": filtered_todos
    }



# Hook函数，用于轻量化的LLMSession before/after函数列表
def todos_before_hook(tool_name: str, args: Dict[str, Any], session) -> Dict[str, Any]:
    """为todos相关工具自动注入session_id"""
    if tool_name in ['create_todos', 'update_todos', 'query_todos']:
        args = args.copy()
        args['session_id'] = session.session_id
    return args


def todos_after_hook(result: Any, tool_name: str, session) -> Any:
    """对todos工具结果进行格式化打印"""
    if tool_name in ['create_todos', 'update_todos', 'query_todos']:
        if isinstance(result, dict) and 'success' in result:
            success_symbol = "✓" if result['success'] else "✗"
            print(f"{tool_name} {success_symbol}\n⎿ {result['msg']}")
            if result.get('data') and tool_name == 'query_todos':
                for todo in result['data']:
                    status_symbol = {"completed": "✓", "in_progress": "●", "pending": "○"}[todo['status']]
                    print(f"  {status_symbol} [{todo['id']}] {todo['content']}")
        else:
            print(f"{tool_name}\n⎿ {result}")
    return result