import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

try:
    r = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": "1"}],
        max_tokens=1,
    )
    print("OK ✅")
    print("usage:", r.usage)
except Exception as e:
    print("Ошибка ❌:", type(e).__name__, "-", e)
