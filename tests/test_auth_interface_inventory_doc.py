"""用户登录与知识库权限接口清单文档测试。"""

import ast
from pathlib import Path


WEB_APP = Path("src/shuyixiao_agent/web_app.py")
INVENTORY_DOC = Path("my_docs/2026-06-10-用户登录与知识库权限接口清单.md")
ROUTE_METHODS = {"get", "post", "delete", "put", "patch"}


def _extract_app_routes():
    """从 web_app.py 静态提取所有 FastAPI 路由。"""
    tree = ast.parse(WEB_APP.read_text(encoding="utf-8"))
    routes = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            func = decorator.func
            if not (
                isinstance(func, ast.Attribute)
                and func.attr in ROUTE_METHODS
                and isinstance(func.value, ast.Name)
                and func.value.id == "app"
            ):
                continue
            if not decorator.args or not isinstance(decorator.args[0], ast.Constant):
                continue

            routes.append(
                {
                    "method": func.attr.upper(),
                    "path": decorator.args[0].value,
                    "line": node.lineno,
                    "handler": node.name,
                }
            )

    return sorted(routes, key=lambda item: (item["line"], item["method"], item["path"]))


def test_interface_inventory_covers_all_fastapi_routes():
    """接口清单必须覆盖 web_app.py 中的所有 HTTP 路由。"""
    doc = INVENTORY_DOC.read_text(encoding="utf-8")
    missing_routes = [
        f"{route['method']} {route['path']}"
        for route in _extract_app_routes()
        if f"| {route['method']} | `{route['path']}` |" not in doc
    ]

    assert missing_routes == []


def test_interface_inventory_marks_auth_categories_and_risky_path_imports():
    """接口清单必须标注鉴权分类、匿名白名单和服务器路径导入接口。"""
    doc = INVENTORY_DOC.read_text(encoding="utf-8")

    for heading in ["匿名白名单", "服务器路径导入接口", "分类口径"]:
        assert heading in doc

    for category in ["公开", "登录用户", "管理员", "legacy 兼容", "下线策略"]:
        assert category in doc

    for anonymous_endpoint in ["`/`", "`/api/health`", "`/api/auth/login`"]:
        assert anonymous_endpoint in doc

    risky_imports = {
        "`/api/rag/upload/file`": "file_path",
        "`/api/rag/upload/directory`": "directory_path",
        "`/api/lpos/contracts/parse`": "file_path",
    }
    for endpoint, risky_field in risky_imports.items():
        assert endpoint in doc
        assert risky_field in doc
