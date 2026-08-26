import os

# Bot tokeni FAQAT Environment Variable orqali beriladi.
# Kodga hech qachon tokenni yozib qo'ymang!
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN environment variable topilmadi! "
        "Render'da Environment bo'limiga BOT_TOKEN qo'shing."
    )

# Admin(lar) Telegram ID raqami(lari). Bir nechta bo'lishi mumkin: "123,456"
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "8824928555").split(",") if x.strip()]

DB_PATH = "kino_bot.db"
