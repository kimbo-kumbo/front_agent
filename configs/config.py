# configs/config.py

# Настройки LLM
MODEL_NAME = "deepseek-flash"
MAX_TOKENS = 500
THINKING_ENABLED = False  # Режим размышлений (True/False)

# Настройки безопасности (Agent Loop)
MAX_STEPS = 8
MAX_TOOL_CALLS = 10
MAX_BUDGET_USD = 0.02

# Настройки путей
WORKSPACE_DIR = "workspace"