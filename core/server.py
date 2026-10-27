import asyncio
import json
import os
import re
import sys
from fastapi import FastAPI, Request
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel
from typing import List
from fastapi.staticfiles import StaticFiles

# Добавляем корневую папку в sys.path, чтобы работали импорты из configs и primitives
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.client import client, log_usage
from configs.config import MODEL_NAME, MAX_TOKENS, THINKING_ENABLED, MAX_STEPS, MAX_TOOL_CALLS, MAX_BUDGET_USD
from primitives.tools import TOOLS_SCHEMA, create_folder, write_file, edit_file, read_multiple_files
from primitives.resources import RESOURCES_SCHEMA, read_file, list_folder
from primitives.validators import VALIDATORS_SCHEMA, validate_html

class LimitUploadSize(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.headers.get('content-length'):
            content_length = int(request.headers.get('content-length'))
            if content_length > 1_000_000: # 1 MB
                return JSONResponse(status_code=413, content={"detail": "Payload Too Large"})
        return await call_next(request)

app = FastAPI(middleware=[Middleware(LimitUploadSize)])

# Объединяем инструменты и ресурсы
ALL_SCHEMAS = TOOLS_SCHEMA + RESOURCES_SCHEMA + VALIDATORS_SCHEMA

AVAILABLE_FUNCTIONS = {
    "create_folder": create_folder,
    "write_file": write_file,
    "read_file": read_file,
    "list_folder": list_folder,
    "edit_file": edit_file, 
    "read_multiple_files": read_multiple_files,
    "validate_html": validate_html,
}

class ChatRequest(BaseModel):
    message: str
    history: List[dict]
    model_name: str = MODEL_NAME
    max_tokens: int = MAX_TOKENS
    max_steps: int = MAX_STEPS
    max_tool_calls: int = MAX_TOOL_CALLS
    max_budget_usd: float = MAX_BUDGET_USD
    thinking_enabled: bool = THINKING_ENABLED
    enable_validation: bool = True

# Определяем путь к workspace
workspace_path = "/app/workspace" if os.path.exists("/app") else "workspace"

@app.get("/")
async def get_index():
    with open(os.path.join(os.path.dirname(__file__), "index.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# --- МАРШРУТЫ ДЛЯ ПРОСМОТРА ФАЙЛОВ ---

# 1. Отдаем сами файлы (HTML, CSS, JS, картинки) для iframe и браузера
if os.path.exists(workspace_path):
    app.mount("/preview", StaticFiles(directory=workspace_path), name="preview")

# 2. Специальный маршрут, чтобы можно было быстро открыть файл с кодом по клику (опционально)
@app.get("/api/files/{file_path:path}")
async def get_file_content(file_path: str):
    # Защита от выхода за пределы
    safe_path = os.path.realpath(os.path.join(workspace_path, file_path))
    if not safe_path.startswith(os.path.realpath(workspace_path)):
        return JSONResponse(status_code=403, content={"detail": "Access denied"})
    if not os.path.exists(safe_path):
        return JSONResponse(status_code=404, content={"detail": "File not found"})
    return FileResponse(safe_path)

# --- ОСНОВНОЙ ЦИКЛ ЧАТА ---

@app.post("/api/chat")
async def chat(request: ChatRequest):
    prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "system_prompt.txt")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read().strip()
    except FileNotFoundError:
        system_prompt = "Ты — ИИ-ассистент."

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(request.history)

    async def event_generator():
        step = 1
        total_spent = 0.0

        while True:
            if step > request.max_steps:
                yield "data: ⚠️ Аварийная остановка: превышен лимит шагов.\n\n"
                break

            yield f"data: [STATUS] Думаю (Шаг {step})...\n\n"
            await asyncio.sleep(0.01)

            resp = await asyncio.to_thread(
                client.chat.completions.create,
                model=request.model_name,
                messages=messages,
                tools=ALL_SCHEMAS,
                tool_choice="auto",
                max_tokens=request.max_tokens,
                extra_body={"thinking": {"type": "enabled" if request.thinking_enabled else "disabled"}}
            )

            step_cost = log_usage(resp, request.model_name, f"WEB (max {request.max_tokens}): {request.message}", thinking=request.thinking_enabled)
            total_spent += step_cost
            
            if total_spent > request.max_budget_usd:
                yield f"data: ⚠️ Аварийная остановка: превышен бюджет задачи (${request.max_budget_usd})!\n\n"
                break

            msg = resp.choices[0].message
            messages.append(msg)

            if msg.tool_calls:
                calls_to_execute = msg.tool_calls[:request.max_tool_calls]
                if len(msg.tool_calls) > request.max_tool_calls:
                    yield f"data: ⚠️ Модель запросила {len(msg.tool_calls)} вызовов, выполняем первые {request.max_tool_calls}.\n\n"
                    dropped_ids = [tc.id for tc in msg.tool_calls[request.max_tool_calls:]]
                    for tc_id in dropped_ids:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "name": "system",
                            "content": "Ошибка: вызов отменен из-за лимита. Продолжи отдельным шагом."
                        })

                for tool_call in calls_to_execute:
                    func_name = tool_call.function.name
                    try:
                        func_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError as e:
                        yield f"data: ⚠️ Ошибка JSON: {e}\n\n"
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": func_name,
                            "content": f"Ошибка: невалидный JSON. {e}"
                        })
                        continue

                    action_text = f"🤖 Вызываю: {func_name}"
                    if func_name == "create_folder": action_text = f"📁 Создаю папку: {func_args.get('path')}"
                    elif func_name == "write_file": action_text = f"📝 Записываю файл: {func_args.get('path')}"
                    elif func_name == "read_file": action_text = f"👁️ Читаю файл: {func_args.get('path')}"
                    elif func_name == "list_folder": action_text = f"📂 Смотрю содержимое рабочей директории"
                        
                    yield f"data: [ACTION] {action_text}\n\n"
                    
                    func_to_call = AVAILABLE_FUNCTIONS.get(func_name)
                    if func_to_call:
                        try:
                            result = func_to_call(**func_args)
                        except Exception as e:
                            result = f"Ошибка: {e}"
                    else:
                        result = f"Ошибка: неизвестная функция {func_name}"

                    safe_result = str(result).replace("\n", "<br>")
                    yield f"data: [RESULT] {safe_result}\n\n"
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": func_name,
                        "content": str(result)
                    })
                
                step += 1
                continue
            else:
                content = msg.content or ""
                if resp.choices[0].finish_reason == "length":
                    content += "\n\n⚠️ **[Ответ оборван из-за лимита токенов.]**"

                content_fixed = re.sub(r'([.!?,:;])([^\s\d])', r'\1 \2', content)
                
                for chunk in content_fixed.split(" "):
                    safe_chunk = chunk.replace("\n", "<br>") 
                    yield f"data: {safe_chunk} \n\n"
                    await asyncio.sleep(0.02)
                
                yield f"data: [COST] 💰 ${total_spent:.6f}\n\n"
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)