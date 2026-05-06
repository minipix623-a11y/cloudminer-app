import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('MINING_BOT_TOKEN')
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:3000')
MINI_APP_URL = os.getenv('MINI_APP_URL', 'https://your-mini-app-url.com')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    args = context.args or []

    # Check for referral code in deep link
    referral_code = None
    if args:
        param = args[0]
        if param.startswith('ref_'):
            referral_code = param[4:]

    # Prepare referral data for Mini App
    referral_data = f"?start=ref_{user.id}" if not referral_code else f"?start=ref_{referral_code}"

    keyboard = [
        [InlineKeyboardButton("⚡ Открыть CloudMiner", web_app={"url": f"{MINI_APP_URL}{referral_data}"})]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        f"⚡ <b>CloudMiner</b> — Привет, {user.first_name}!\n\n"
        "Покупай виртуальные майнеры, зарабатывай Credits!\n"
        "Это демо-версия — валюта игровая, не реальная.\n\n"
        "Нажми кнопку чтобы открыть приложение:"
    )

    await update.message.reply_text(welcome_text, parse_mode="HTML", reply_markup=reply_markup)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ <b>CloudMiner Help</b>\n\n"
        "/start — открыть приложение\n"
        "/help — помощь\n"
        "/balance — проверить баланс\n\n"
        "❓ Поддержка: @MrDimka_support\n\n"
        "⚠️ Это игровая симуляция. Валюта виртуальная.",
        parse_mode="HTML"
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        import requests
        resp = requests.get(f"{BACKEND_URL}/api/user/{user_id}", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            balance = data.get('balance', 0)
            await update.message.reply_text(f"💰 Баланс: <b>{balance:.2f}$</b>", parse_mode="HTML")
        else:
            await update.message.reply_text("❌ Не удалось получить баланс. Попробуй /start")
    except Exception as e:
        await update.message.reply_text("💰 Баланс: <b>0.00$</b>\n(Демо-режим)", parse_mode="HTML")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handlers([
        CommandHandler("start", start),
        CommandHandler("help", help_cmd),
        CommandHandler("balance", balance),
    ])

    print("CloudMiner Bot started!")
    print(f"Mini App URL: {MINI_APP_URL}")
    app.run_polling()

if __name__ == "__main__":
    main()
