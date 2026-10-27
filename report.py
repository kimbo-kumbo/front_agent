import csv
from collections import defaultdict
import os

LOG_FILE = os.path.join(os.path.dirname(__file__), "workspace", "usage_log.csv")

def load_rows(path: str = LOG_FILE):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def fmt_usd(x: float) -> str:
    return f"${x:.8f}  (≈ {x*100:.6f} центов)"

def get_ts(r: dict) -> str:
    return r.get("ts_utc") or r.get("ts") or ""

def main():
    rows = load_rows()
    if not rows:
        print("Лог пуст.")
        return

    total_cost = 0.0
    total_tokens = 0
    total_hit = total_miss = total_completion = 0

    by_day = defaultdict(float)
    by_model = defaultdict(float)
    by_period = defaultdict(float)
    by_thinking = defaultdict(float) # <--- НОВЫЙ СЛОВАРЬ

    for r in rows:
        cost = float(r["cost_usd"])
        hit = int(r.get("cache_hit", 0) or 0)
        miss = int(r.get("cache_miss", 0) or 0)
        comp = int(r.get("completion_tokens", 0) or 0)
        tok = int(r.get("total_tokens", 0) or 0)
        model = r.get("model", "?")
        model = model.replace("deepseek-", "") 
        period = r.get("period", "unknown")
        
        # Читаем thinking. Если поля нет (старые логи), пишем "old_log"
        thinking_raw = r.get("thinking", "old_log")
        thinking = "ON" if thinking_raw in (True, "True") else ("OFF" if thinking_raw in (False, "False") else "unknown")
        
        day = get_ts(r)[:10] or "unknown"

        total_cost += cost
        total_tokens += tok
        total_hit += hit
        total_miss += miss
        total_completion += comp

        by_day[day] += cost
        by_model[model] += cost
        by_period[period] += cost
        by_thinking[thinking] += cost # <--- ДОБАВИЛИ АГРЕГАЦИЮ

    print("═" * 60)
    print(f"Запросов: {len(rows)}")
    print(f"Токенов:  {total_tokens}  "
          f"(prompt: {total_hit + total_miss}, cache_hit: {total_hit}, "
          f"cache_miss: {total_miss}, completion: {total_completion})")
    print(f"Стоимость: {fmt_usd(total_cost)}")
    print("═" * 60)

    print("\nПо режиму (thinking):")
    for t, c in sorted(by_thinking.items(), key=lambda x: -x[1]):
        print(f"  {t:<10} {fmt_usd(c)}")

    print("\nПо моделям:")
    for m, c in sorted(by_model.items(), key=lambda x: -x[1]):
        print(f"  {m:<18} {fmt_usd(c)}")

    print("\nПо периодам (peak/off_peak):")
    for p, c in sorted(by_period.items(), key=lambda x: -x[1]):
        print(f"  {p:<10} {fmt_usd(c)}")

    print("\nПо дням (UTC):")
    for d, c in sorted(by_day.items()):
        print(f"  {d}  {fmt_usd(c)}")

if __name__ == "__main__":
    main()