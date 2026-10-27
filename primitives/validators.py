# primitives/validators.py
from html.parser import HTMLParser

class HTMLValidator(HTMLParser):
    def __init__(self):
        super().__init__()
        self.errors = []
        self.stack = []
        self.unclosed_tags = {'div', 'p', 'span', 'a', 'ul', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'button'}

    def handle_starttag(self, tag, attrs):
        if tag in self.unclosed_tags:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.unclosed_tags:
            if self.stack and self.stack[-1] == tag:
                self.stack.pop()
            else:
                self.errors.append(f"Неожиданный закрывающий тег </{tag}>")

def validate_html(content: str) -> str:
    parser = HTMLValidator()
    parser.feed(content)
    
    if not parser.errors and not parser.stack:
        return "✅ HTML валиден. Ошибок не найдено."
        
    result = []
    if parser.errors:
        result.append("Найдены ошибки в структуре:")
        result.extend(parser.errors)
    if parser.stack:
        result.append("Незакрытые теги: " + ", ".join(parser.stack))
        
    return "\n".join(result)

VALIDATORS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "validate_html",
            "description": "Проверяет HTML-код на наличие незакрытых тегов и структурных ошибок. Передавай сюда САМ КОД, а не путь к файлу.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "HTML-код для проверки"}
                },
                "required": ["content"]
            }
        }
    }
]