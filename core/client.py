import os
import csv
from datetime import datetime, timezone
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

PRICES = {
    "deepseek-flash": {
        "peak":     {"hit": 0.006, "miss": 0.30, "out": 1.20},
        "off_peak": {"hit": 0.003, "miss": 0.15, "out": 0.60},
    },
    "deepseek-v4-pro": {
        "peak":     {"hit": 0.044, "miss": 1.32, "out": 3.96},
        "off_peak": {"hit": 0.022, "miss": 0.66, "out": 1.98},
    },
}

HOLIDAYS_CN = set()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

# Логи пишем в workspace, чтобы они сохранялись на хосте (в Docker)
if os.path.exists("/app"):
    LOG_FILE = "/app/workspace/usage_log.csv"
else:
    LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace", "usage_log.csv")

def is_peak(dt_utc: datetime) -> bool:
    if dt_utc.date().isoformat() in HOLIDAYS_CN:
        return False
    if dt_utc.weekday() >= 5:
        return False
    m = dt_utc.hour * 60 + dt_utc.minute
    return (1 * 60) <= m < (4 * 60) or (6 * 60) <= m < (10 * 60)

# ── НОВАЯ ФУНКЦИЯ ЛОГИРОВАНИЯ ──────────────────────────────────────────────
def log_usage(resp, model: str, prompt_text: str, thinking: bool = False):
    """Считает стоимость ответа и записывает его в CSV-лог."""
    u = resp.usage
    now_utc = datetime.now(timezone.utc)
    period = "peak" if is_peak(now_utc) else "off_peak"
    p = PRICES[model][period]

    # Безопасно достаем токены кэша (на случай, если их нет в ответе)
    hit = getattr(u, "prompt_cache_hit_tokens", 0) or 0
    miss = getattr(u, "prompt_cache_miss_tokens", 0) or 0
    if hit == 0 and miss == 0:
        miss = u.prompt_tokens

    # Считаем стоимость
    cost = (
        miss * p["miss"] / 1_000_000
        + hit * p["hit"] / 1_000_000
        + u.completion_tokens * p["out"] / 1_000_000
    )

    short_model = model.replace("deepseek-", "") 

    row = {
        "ts_utc": now_utc.isoformat(timespec="seconds"),
        "period": period,
        "model": short_model,
        "thinking": thinking,
        "finish_reason": resp.choices[0].finish_reason,
        "prompt_tokens": u.prompt_tokens,
        "cache_hit": hit,
        "cache_miss": miss,
        "completion_tokens": u.completion_tokens,
        "total_tokens": u.total_tokens,
        "cost_usd": f"{cost:.8f}",
        "prompt": prompt_text[:80].replace("\n", " "),
    }
    
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            w.writeheader()
        w.writerow(row)
        
    return cost  # <--- ДОБАВЛЯЕМ ВОЗВРАТ СТОИМОСТИ
# ───────────────────────────────────────────────────────────────────────────

def ask(prompt: str, model: str = "deepseek-flash", max_tokens: int = 300, thinking: bool = False) -> str:
    if model not in PRICES:
        raise ValueError(f"Неизвестная модель {model!r}. Доступно: {list(PRICES)}")

    extra_body = {"thinking": {"type": "enabled" if thinking else "disabled"}}

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        extra_body=extra_body,
    )

    # Вызываем нашу новую функцию логирования
    log_usage(resp, model, prompt, thinking)

    return resp.choices[0].message.content


if __name__ == "__main__":
    prompt_ru = "Придумай имя папки для Python-проекта, одно слово латиницей."
    answer = ask(prompt_ru, thinking=True)
    print("Ответ:", answer)
    print("Лог:", LOG_FILE)