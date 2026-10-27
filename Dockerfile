FROM python:3.12-slim

RUN useradd -m -u 1000 agent
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=agent:agent . .

USER agent
EXPOSE 8000

CMD ["python", "core/server.py"]