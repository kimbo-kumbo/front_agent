import os

# Сразу делаем WORKSPACE абсолютным и физическим (разворачиваем симлинки)
WORKSPACE = os.path.realpath(os.path.join(os.path.dirname(__file__), "workspace"))
os.makedirs(WORKSPACE, exist_ok=True)

# Список запрещённых директорий (на всякий случай)
FORBIDDEN_DIRS = ["/etc", "/proc", "/sys", "/dev", "/root"]

def get_workspace_path(relative_path: str) -> str:
    """Защита от выхода за пределы WORKSPACE (path traversal + симлинки)."""
    joined = os.path.join(WORKSPACE, relative_path)
    target = os.path.realpath(joined)
    
    # Проверка на выход за пределы WORKSPACE
    if not (target == WORKSPACE or target.startswith(WORKSPACE + os.sep)):
        raise ValueError(f"Доступ запрещен: путь {relative_path} вне рабочей директории.")
    
    # Дополнительная проверка (на случай, если WORKSPACE скомпрометирован)
    for forbidden in FORBIDDEN_DIRS:
        if target.startswith(forbidden):
            raise ValueError(f"Доступ запрещен: путь {relative_path} ведёт в защищённую директорию.")
    
    return target

# ── Функции (без изменений) ──────────────────────────────────────────────

def create_folder(path: str) -> str:
    try:
        full_path = get_workspace_path(path)
        os.makedirs(full_path, exist_ok=True)
        return f"Папка успешно создана: {path}"
    except Exception as e:
        return f"Ошибка: {e}"

def write_file(path: str, content: str) -> str:
    try:
        full_path = get_workspace_path(path)
        parent_dir = os.path.dirname(full_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Файл успешно записан: {path} ({len(content)} символов)"
    except Exception as e:
        return f"Ошибка: {e}"

def read_file(path: str) -> str:
    try:
        full_path = get_workspace_path(path)
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content if content else "Файл пуст."
    except Exception as e:
        return f"Ошибка: {e}"

def list_folder(path: str = ".") -> str:
    try:
        full_path = get_workspace_path(path)
        if not os.path.exists(full_path):
            return f"Ошибка: папка {path} не существует."
        items = os.listdir(full_path)
        if not items:
            return f"Папка {path} пуста."
        result = []
        for item in items:
            item_path = os.path.join(full_path, item)
            item_type = "DIR" if os.path.isdir(item_path) else "FILE"
            result.append(f"[{item_type}] {item}")
        return "\n".join(result)
    except Exception as e:
        return f"Ошибка: {e}"

# ── Схемы для LLM (описываем функции для нейросети) ──────────────────────────

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "create_folder",
            "description": "Создает новую папку по указанному пути.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Относительный путь к папке (например, 'my_project')"}},
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Записывает текст в файл. Если файла или папки нет, они будут созданы.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Путь к файлу (например, 'my_project/main.py')"},
                    "content": {"type": "string", "description": "Текст, который нужно записать в файл"}
                },
                "required": ["path", "content"]
            }
        }
    },
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
            "description": "Показывает список файлов и папок в указанной директории.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Путь к папке. По умолчанию текущая."}},
                "required": []
            }
        }
    }
]