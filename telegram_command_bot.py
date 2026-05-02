from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.config import settings
from app.main import publish_one_fact


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


async def post_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return

    await update.message.reply_text("Запускаю створення поста...")

    try:
        result = await asyncio.to_thread(publish_one_fact)
        if result is None:
            await update.message.reply_text(
                "Пост не створився або не опублікувався. Перевір лог і спробуй ще раз."
            )
            return

        await update.message.reply_text(
            f"Пост опубліковано ✅\n"
            f"Назва: {result.title}\n"
            f"Telegram Message ID: {result.telegram_message_id}\n"
            f"Запис у таблицю: виконано"
        )
    except Exception as exc:
        logger.exception("Failed to run /post command: %s", exc)
        await update.message.reply_text(f"Сталася помилка під час публікації: {exc}")


def main() -> None:
    if not settings.telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not configured")

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("post", post_command))

    logger.info("Telegram command bot started. Use /post to publish a post.")
    app.run_polling()


if __name__ == "__main__":
    main()
