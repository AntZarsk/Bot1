from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from app.telegram_publisher import publish_to_telegram


def main() -> None:
    load_dotenv()

    image_path = Path("test_telegram.jpg")
    if not image_path.exists():
        raise FileNotFoundError(
            "test_telegram.jpg not found. Put any image with this name in the project root."
        )

    caption = "Тестовий пост ✅\nЯкщо ти бачиш це в каналі, Telegram-публікація фото працює."
    message_id = publish_to_telegram(str(image_path), caption)
    print(f"Telegram test sent. Message ID: {message_id}")


if __name__ == "__main__":
    main()
