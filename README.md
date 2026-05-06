# CloudMiner Mini App

Telegram Mini App Demo — игровая симуляция майнинга.

## Quick Start

```bash
cd mining_app
pip install flask python-telegram-bot python-dotenv
```

## Запуск

```bash
# Терминал 1 — Backend
cd backend
python app.py

# Терминал 2 — Bot (в отдельном окне)
cd backend
python bot.py
```

## Структура

- `backend/app.py` — Flask API сервер
- `backend/bot.py` — Telegram бот
- `frontend/index.html` — Mini App (WebApp)

## ⚠️ Demo

Валюта виртуальная (Credits). Нет реальных платежей и вывода.