import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

def inspect():
    print("Отправляем запрос...")
    resp = client.chat.completions.create(
        model="deepseek-flash",
        messages=[{"role": "user", "content": "Say 'hello'"}],
        max_tokens=10,
        extra_body={"thinking": {"type": "disabled"}},
    )

    print("\n" + "="*50)
    print("1. ВЕСЬ ОТВЕТ ЦЕЛИКОМ (JSON):")
    print("="*50)
    # model_dump_json() выведет абсолютно все поля, которые вернул сервер
    print(resp.model_dump_json(indent=2))

    print("\n" + "="*50)
    print("2. РАЗБОР ПО КЛЮЧЕВЫМ ПОЛЯМ:")
    print("="*50)
    
    print(f"ID запроса (resp.id): {resp.id}")
    print(f"Модель (resp.model): {resp.model}")
    print(f"Время (resp.created): {resp.created}")
    
    choice = resp.choices[0]
    print(f"Причина остановки (finish_reason): {choice.finish_reason}")
    print(f"Текст ответа: {choice.message.content!r}")
    
    # Проверяем, есть ли поле с мыслями (даже если thinking выключен)
    reasoning = getattr(choice.message, "reasoning_content", None)
    print(f"Мысли модели (reasoning_content): {reasoning!r}")

    print("\n--- USAGE (Токены) ---")
    u = resp.usage
    print(f"prompt_tokens: {u.prompt_tokens}")
    print(f"completion_tokens: {u.completion_tokens}")
    print(f"total_tokens: {u.total_tokens}")
    
    # Специфичные для DeepSeek поля кэша
    print(f"prompt_cache_hit_tokens: {getattr(u, 'prompt_cache_hit_tokens', 'НЕТ ПОЛЯ')}")
    print(f"prompt_cache_miss_tokens: {getattr(u, 'prompt_cache_miss_tokens', 'НЕТ ПОЛЯ')}")
    
    # Детализация (если есть)
    details = getattr(u, 'prompt_tokens_details', None)
    if details:
        print(f"prompt_tokens_details: {details}")

if __name__ == "__main__":
    inspect()