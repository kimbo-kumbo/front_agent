import os
import json
from client import client, log_usage
from tools import TOOLS_SCHEMA, create_folder, write_file, read_file, list_folder

AVAILABLE_TOOLS = {
    "create_folder": create_folder,
    "write_file": write_file,
    "read_file": read_file,
    "list_folder": list_folder,
}

def run_agent(user_prompt: str, model: str = "deepseek-flash", max_tokens: int = 500):
    print(f"\n[Пользователь]: {user_prompt}")
    
    messages = [
        {"role": "system", "content": "Ты — ИИ-ассистент. Твоя задача — выполнять команды пользователя, используя доступные инструменты. Не стесняйся вызывать несколько инструментов подряд. Если задача выполнена, напиши финальный ответ."},
        {"role": "user", "content": user_prompt}
    ]

    # ── НАСТРОЙКИ БЕЗОПАСНОСТИ ──
    MAX_STEPS = 8               # Максимум 8 итераций (вызовов API)
    MAX_TOOL_CALLS = 5          # Максимум 5 инструментов за один шаг
    MAX_BUDGET_USD = 0.01       # Лимит трат: 1 цент на задачу
    total_spent = 0.0           # Счетчик потраченных денег
    # ────────────────────────────

    step = 1
    while True:
        # ЗАЩИТА 1: Лимит шагов
        if step > MAX_STEPS:
            print(f"\n⚠️ АВАРИЙНАЯ ОСТАНОВКА: агент превысил лимит в {MAX_STEPS} шагов!")
            break

        print(f"\n--- Шаг {step} ---")
        
        # 1. Отправляем запрос в LLM
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto",
            max_tokens=max_tokens,
            extra_body={"thinking": {"type": "disabled"}}
        )

        # 2. Логируем ответ и получаем стоимость шага
        step_cost = log_usage(resp, model, f"AGENT: {user_prompt}", thinking=False)
        total_spent += step_cost
        print(f"💰 Стоимость шага: ${step_cost:.6f} | Всего потрачено: ${total_spent:.6f}")

        # ЗАЩИТА 2: Лимит бюджета
        if total_spent > MAX_BUDGET_USD:
            print(f"\n⚠️ АВАРИЙНАЯ ОСТАНОВКА: превышен бюджет задачи (${MAX_BUDGET_USD})!")
            break

        msg = resp.choices[0].message
        messages.append(msg)

        # 3. Проверяем, хочет ли модель вызвать инструмент
        if msg.tool_calls:
            calls_to_execute = msg.tool_calls[:MAX_TOOL_CALLS]
            
            if len(msg.tool_calls) > MAX_TOOL_CALLS:
                print(f"⚠️ Модель запросила {len(msg.tool_calls)} вызовов, но мы выполним только первые {MAX_TOOL_CALLS}.")
            
            for tool_call in calls_to_execute:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)
                
                print(f"🤖 Модель решила вызвать: {func_name} с аргументами {func_args}")
                
                func_to_call = AVAILABLE_TOOLS.get(func_name)
                if func_to_call:
                    try:
                        result = func_to_call(**func_args)
                    except Exception as e:
                        result = f"Ошибка при выполнении: {e}"
                else:
                    result = f"Ошибка: неизвестная функция {func_name}"

                print(f"🔧 Результат: {result}")

                # 4. Возвращаем результат обратно в модель
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": func_name,
                    "content": str(result)
                })
            
            step += 1
            continue # Идём на следующий круг
            
        else:
            # Если tool_calls нет, значит это финальный текстовый ответ
            print(f"\n[Агент]: {msg.content}")
            print(f"🏁 Задача завершена. Итого потрачено: ${total_spent:.6f}")
            break

if __name__ == "__main__":
    os.makedirs("workspace", exist_ok=True)
    
    # Тест 1: Нормальная задача (должна выполниться за 2-3 шага)
    task_ok = "Создай папку 'my_cool_project'. Внутри нее создай файл 'hello.py', в который напиши код на Python, выводящий 'Hello from DeepSeek!'. Затем выведи список файлов в этой папке."
    run_agent(task_ok, max_tokens=300)

    # Тест 2 (раскомментируй, чтобы проверить защиту от зацикливания):
    #task_loop = "Пытайся прочитать файл 'nonexistent.txt' 10 раз подряд, даже если получаешь ошибку."
    #run_agent(task_loop)