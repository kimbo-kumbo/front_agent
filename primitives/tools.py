# primitives/tools.py
import os
from primitives.resources import get_workspace_path
from core.memory import search_knowledge as db_search

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

def read_multiple_files(paths: list[str]) -> str:
    """Читает несколько файлов и возвращает их содержимое с заголовками."""
    result = []
    for path in paths:
        try:
            full_path = get_workspace_path(path)
            if not os.path.exists(full_path):
                result.append(f"=== Файл: {path} ===\n[Ошибка: файл не найден]")
                continue
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            result.append(f"=== Файл: {path} ===\n{content}\n{'='*30}")
        except Exception as e:
            result.append(f"=== Файл: {path} ===\n[Ошибка: {e}]")
    return "\n\n".join(result)

def edit_file(path: str, search_text: str, replace_text: str) -> str:
    """Ищет кусок текста в файле и заменяет его на новый."""
    try:
        full_path = get_workspace_path(path)
        if not os.path.exists(full_path):
            return f"Ошибка: файл {path} не найден."
            
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        if search_text not in content:
            return f"Ошибка: указанный фрагмент для поиска не найден в файле {path}."
            
        # Ограничиваем замену, чтобы не убить весь файл
        if content.count(search_text) > 1:
            return f"Ошибка: фрагмент встречается в файле {content.count(search_text)} раз. Уточни поиск (добавь больше контекста), чтобы заменить только нужное место."
            
        new_content = content.replace(search_text, replace_text)
        
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(new_content)
            
        return f"Файл {path} успешно отредактирован."
    except Exception as e:
        return f"Ошибка при редактировании: {e}"

def search_knowledge_base(query: str) -> str:
    """Обертка для поиска в векторной БД."""
    try:
        return db_search(query)
    except Exception as e:
        return f"Ошибка поиска: {e}"

# Схемы для LLM
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
                    "path": {"type": "string", "description": "Путь к файлу"},
                    "content": {"type": "string", "description": "Текст, который нужно записать в файл"}
                },
                "required": ["path", "content"]
            }
        }
    },
        {
        "type": "function",
        "function": {
            "name": "read_multiple_files",
            "description": "Читает содержимое сразу нескольких файлов. Полезно, когда нужно проанализировать проект.",
            "parameters": {
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Список путей к файлам (например, ['index.html', 'style.css'])"
                    }
                },
                "required": ["paths"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Точечно редактирует файл: ищет старый текст и заменяет его на новый. Позволяет не переписывать весь файл целиком.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Путь к файлу"},
                    "search_text": {"type": "string", "description": "Точный кусок текста, который нужно найти и заменить (включая пробелы и отступы)"},
                    "replace_text": {"type": "string", "description": "Новый текст, который встанет на место старого"}
                },
                "required": ["path", "search_text", "replace_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Ищет информацию по смыслу во всех файлах проекта (векторный поиск). Используй, если не знаешь, в каком файле находится нужный код или переменная.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Вопрос или фраза для поиска (например, 'где задан цвет кнопки')"}
                },
                "required": ["query"]
            }
        }
    }
]