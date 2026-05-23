"""
Mr. Scrapper — Telegram Bot
Commands: /start, /buscar, /status
Communicates with the FastAPI backend via HTTP.
"""

import logging
import os

import httpx
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
)
logger = logging.getLogger("mr_scrapper_bot")

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# We store a user JWT token in memory for auth
# In production, you'd want a more robust auth flow
AUTH_TOKEN: str | None = None


async def _api_post(path: str, json_data: dict | None = None) -> dict:
    """POST request to backend API."""
    headers = {}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30.0) as client:
        resp = await client.post(path, json=json_data, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def _api_get(path: str) -> dict:
    """GET request to backend API."""
    headers = {}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30.0) as client:
        resp = await client.get(path, headers=headers)
        resp.raise_for_status()
        return resp.json()


# ─────────────────────────────────────────────────────────────────
# /start
# ─────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message."""
    await update.message.reply_text(
        "🎬 *Mr\\. Scrapper Bot*\n\n"
        "Comandos disponíveis:\n"
        "• `/buscar <termo> <quantidade>` — Iniciar scraping\n"
        "• `/status` — Ver progresso atual\n"
        "• `/login <email> <senha>` — Autenticar\\-se\n\n"
        "Exemplo: `/buscar nature 10`",
        parse_mode="MarkdownV2",
    )


# ─────────────────────────────────────────────────────────────────
# /login <email> <password>
# ─────────────────────────────────────────────────────────────────

async def cmd_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Authenticate with the backend."""
    global AUTH_TOKEN

    if len(context.args) < 2:
        await update.message.reply_text("Uso: /login <email> <senha>")
        return

    email, password = context.args[0], context.args[1]

    try:
        data = await _api_post("/api/auth/login", {"email": email, "password": password})
        AUTH_TOKEN = data.get("access_token")
        await update.message.reply_text("✅ Login realizado com sucesso!")
    except httpx.HTTPStatusError as e:
        detail = e.response.json().get("detail", "Erro desconhecido")
        await update.message.reply_text(f"❌ Falha no login: {detail}")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {e}")


# ─────────────────────────────────────────────────────────────────
# /buscar <term> <count>
# ─────────────────────────────────────────────────────────────────

async def cmd_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a scraping task."""
    if not AUTH_TOKEN:
        await update.message.reply_text("⚠️ Faça login primeiro com /login <email> <senha>")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Uso: /buscar <termo> <quantidade>\nExemplo: /buscar nature 10")
        return

    query = " ".join(context.args[:-1])
    try:
        target_count = int(context.args[-1])
    except ValueError:
        await update.message.reply_text("❌ A quantidade deve ser um número inteiro.")
        return

    try:
        data = await _api_post(
            "/api/scraper/start",
            {"query": query, "target_count": target_count},
        )
        await update.message.reply_text(
            f"🚀 Scraping iniciado!\n\n"
            f"🔍 Busca: *{query}*\n"
            f"🎯 Meta: *{target_count}* vídeos\n\n"
            f"Use /status para acompanhar o progresso.",
            parse_mode="Markdown",
        )
    except httpx.HTTPStatusError as e:
        detail = e.response.json().get("detail", "Erro desconhecido")
        await update.message.reply_text(f"❌ Erro: {detail}")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao iniciar scraping: {e}")


# ─────────────────────────────────────────────────────────────────
# /status
# ─────────────────────────────────────────────────────────────────

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check scraping task status."""
    if not AUTH_TOKEN:
        await update.message.reply_text("⚠️ Faça login primeiro com /login <email> <senha>")
        return

    try:
        data = await _api_get("/api/scraper/status")

        if not data.get("is_running"):
            await update.message.reply_text("💤 Nenhuma tarefa de scraping em execução.")
            return

        progress = data.get("progress_percent", 0)
        bar_filled = int(progress / 5)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)

        msg = (
            f"📊 *Status do Scraping*\n\n"
            f"🔍 Busca: `{data.get('query', '—')}`\n"
            f"🎯 Meta: {data.get('target_count', 0)}\n"
            f"✅ Baixados: {data.get('downloaded_count', 0)}\n"
            f"❌ Falhas: {data.get('failed_count', 0)}\n\n"
            f"`[{bar}] {progress:.1f}%`"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao consultar status: {e}")


# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────

def main():
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set. Exiting.")
        return

    logger.info("🤖 Starting Mr. Scrapper Telegram Bot...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("login", cmd_login))
    app.add_handler(CommandHandler("buscar", cmd_buscar))
    app.add_handler(CommandHandler("status", cmd_status))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
