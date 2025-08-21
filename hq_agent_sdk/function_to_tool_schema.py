from __future__ import annotations
import inspect
import json
import re
from typing import (
    Any, get_origin, get_args, Union, Optional, List, Dict, Tuple, Literal, Mapping, Sequence
)

# --------- 简单的 docstring 解析（支持 Google/NumPy/Sphinx :param: 风格的一部分）---------
_PARAM_DESC_RE = re.compile(r":param\s+(\w+)\s*:\s*(.+)")
def parse_docstring(func) -> tuple[str, dict]:
    doc = inspect.getdoc(func) or ""
    lines = doc.splitlines()
    description = ""
    if lines:
        # 首段非空行作为工具描述
        for ln in lines:
            if ln.strip():
                description = ln.strip()
                break
    param_desc = {}
    for m in _PARAM_DESC_RE.finditer(doc):
        param_desc[m.group(1)] = m.group(2).strip()
    return description, param_desc

# --------- Python 类型 -> JSON Schema 子集 映射 ----------
def python_type_to_schema(py_type: Any) -> dict:
    """
    将 Python 注解映射为 JSON Schema 子集：
    - 基础: str/int/float/bool
    - list[T], tuple[T...], dict[str, V]
    - Union / Optional
    - Literal[...] 转 enum
    - 未知类型按 "string" + format=object_repr 兜底
    """
    # 无注解
    if py_type is inspect._empty:
        return {"type": "string"}  # 合理兜底

    origin = get_origin(py_type)
    args = get_args(py_type)

    # Literal -> enum
    if origin is Literal:
        # 允许 Literal 混合类型；推断基础 type
        enum_vals = list(args)
        base_types = {type(v) for v in enum_vals}
        json_type = None
        if base_types <= {str}:
            json_type = "string"
        elif base_types <= {int}:
            json_type = "integer"
        elif base_types <= {float, int}:  # 混合当 number
            json_type = "number"
        elif base_types <= {bool}:
            json_type = "boolean"
        else:
            json_type = "string"
        return {"type": json_type, "enum": enum_vals}

    # Optional[T] = Union[T, None]
    if origin is Union:
        # 过滤 NoneType
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            sub = python_type_to_schema(non_none[0])
            # 使用 anyOf + nullable 表意更清晰（很多实现也直接不写 nullable）
            return {"anyOf": [sub, {"type": "null"}]}
        else:
            # 一般 Union，合并 anyOf
            return {"anyOf": [python_type_to_schema(a) for a in args]}

    # list/sequence
    if origin in (list, List, Sequence):
        item_t = args[0] if args else Any
        return {"type": "array", "items": python_type_to_schema(item_t)}

    # tuple
    if origin in (tuple, Tuple):
        if not args or args == ((),):
            return {"type": "array"}
        # 固定长度元组
        return {
            "type": "array",
            "prefixItems": [python_type_to_schema(a) for a in args],
            "minItems": len(args),
            "maxItems": len(args),
        }

    # dict / mapping（简化为 string key）
    if origin in (dict, Dict, Mapping):
        val_t = args[1] if len(args) == 2 else Any
        return {
            "type": "object",
            "additionalProperties": python_type_to_schema(val_t)
        }

    # 基础类型
    if py_type in (str,):
        return {"type": "string"}
    if py_type in (int,):
        return {"type": "integer"}
    if py_type in (float,):
        return {"type": "number"}
    if py_type in (bool,):
        return {"type": "boolean"}

    # 兜底：未知类型按字符串表示
    return {"type": "string", "format": "object_repr"}

# --------- 函数 -> 工具 schema ----------
def function_to_tool_schema(func) -> dict:
    """
    将 Python 函数反射为“工具声明 + 参数 JSON Schema 子集”。
    输出示例结构：
    {
      "name": "get_weather",
      "description": "...",
      "parameters": {
        "type": "object",
        "properties": { ... },
        "required": ["city"]
      }
    }
    """
    sig = inspect.signature(func)
    description, param_desc = parse_docstring(func)

    # 获取完整类型提示（支持 from __future__ annotations）
    try:
        type_hints = typing.get_type_hints(func)
    except Exception:
        # 某些前向引用/运行环境下可能失败，退化为空
        type_hints = {}

    properties = {}
    required = []
    for name, param in sig.parameters.items():
        if name in ("self", "cls"):
            continue

        ann = type_hints.get(name, param.annotation)
        schema = python_type_to_schema(ann)

        # 描述
        desc = param_desc.get(name)
        if desc:
            schema["description"] = desc

        # 默认值
        if param.default is not inspect._empty:
            schema["default"] = param.default
        else:
            # 无默认 = 必填（注意 Optional 只影响类型，不等于有默认）
            required.append(name)

        properties[name] = schema

    parameters_schema = {
        "type": "object",
        "properties": properties,
    }
    if required:
        parameters_schema["required"] = required

    tool_schema = {
        "name": func.__name__,
        "description": description or f"Tool function {func.__name__}",
        "parameters": parameters_schema,
    }
    return tool_schema

# --------- 示例 ----------
# 枚举：用 Literal；可选：用 Optional；列表/字典/联合类型均可
from typing import TypedDict
import typing

def get_weather(
    city: str,
    unit: Literal["C", "F"] = "C",
    days: Optional[int] = None,
    tags: list[str] = [],
    extras: dict[str, Union[str, int]] = {},
):
    """
    查询城市天气的工具。
    city: 目标城市名
    unit: 温度单位（C 或 F）
    days: 未来预报天数（可选）
    tags: 过滤标签（可选）
    extras: 额外参数（键为字符串）
    """
    raise NotImplementedError

if __name__ == "__main__":
    schema = function_to_tool_schema(get_weather)
    print(json.dumps(schema, ensure_ascii=False, indent=2))
