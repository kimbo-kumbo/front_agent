# primitives/resources.py
import os

if os.path.exists("/app"):
    WORKSPACE = "/app/workspace"
else:
    WORKSPACE = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "workspace"))

def get_workspace_path(relative_path: str) -> str:
    joined = os.path.join(WORKSPACE, relative_path)
    target = os.path.realpath(joined)
    if not (target == WORKSPACE or target.startswith(WORKSPACE + os.sep)):
        raise ValueError(f"Доступ запрещен: путь {relative_path} вне рабочей директории.")
    return target

def read_file(path: str) -> str:
    try:
        full_path = get_workspace_path(path)
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content if content else "Файл пуст."
    except Exception as e:
        return f"Ошибка: {e}"

def list_folder() -> str:
    try:
        if not os.path.exists(WORKSPACE):
            return "Рабочая директория пуста."
        result = []
        def walk_dir(current_path, relative_prefix=""):
            try:
                items = sorted(os.listdir(current_path))
            except PermissionError:
                return
            for item in items:
                if item in ['__pycache__', '.git']: continue
                item_path = os.path.join(current_path, item)
                rel_path = os.path.join(relative_prefix, item)
                if os.path.isdir(item_path):
                    result.append(f"{rel_path}/")
                    walk_dir(item_path, rel_path)
                else:
                    result.append(rel_path)
        walk_dir(WORKSPACE)
        if not result: return "Рабочая директория пуста."
        return "Структура проекта (относительные пути):\n" + "\n".join(result)
    except Exception as e:
        return f"Ошибка: {e}"

# Схемы для LLM
RESOURCES_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Читает содержимое файла.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Путь к файлу"}},
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_folder",
            "description": "Показывает список всех файлов и папок в корневой рабочей директории.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
]