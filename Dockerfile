FROM python:3.12-slim

# ── Безопасность ─────────────────────────────────
# Создаём непривилегированного пользователя
RUN useradd -m -u 1000 agent
# ─────────────────────────────────────────────────

WORKDIR /app

# Устанавливаем зависимости (от root, чтобы не мешать правам)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходники и делаем владельцем нашего пользователя
COPY --chown=agent:agent . .

# Переключаемся на пользователя agent
USER agent

# По умолчанию — запуск агента
CMD ["python", "agent.py"]