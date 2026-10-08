import asyncio
import html
import logging
import os
from aiohttp import web

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandStart
from aiogram.types import Message

BOT_TOKEN = "8450913787:AAGFDmWAjUc2XQu_4du6z8p_7KXf1V4FYuM"
SUPERADMIN_ID = 5592043053

ADMIN_IDS = [
    5592043053,
]

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    name = html.escape(message.from_user.first_name or "ученик")
    await message.answer(
        f"👋 Привет, <b>{name}</b>!\n\n"
        "Напиши своё анонимное сообщение, и оно будет передано администрации."
    )


@router.message(F.text & ~F.text.startswith("/"))
async def handle_user_text(message: Message, bot: Bot):
    user = message.from_user
    text = html.escape(message.text)

    admin_text = f"📩 <b>Новое сообщение:</b>\n\n{text}"
    for admin_id in ADMIN_IDS:
        if admin_id == SUPERADMIN_ID:
            continue
        try:
            await bot.send_message(admin_id, admin_text)
        except TelegramAPIError as e:
            logging.warning("Не удалось отправить админу %s: %s", admin_id, e)

    username = f"@{user.username}" if user.username else "нет username"
    super_text = (
        "📩 <b>Новое сообщение</b>\n\n"
        f"👤 Имя: {html.escape(user.full_name)}\n"
        f"🔗 Username: {html.escape(username)}\n"
        f"🆔 ID: <code>{user.id}</code>\n\n"
        f"💬 Текст:\n{text}"
    )
    try:
        await bot.send_message(SUPERADMIN_ID, super_text)
    except TelegramAPIError as e:
        logging.warning("Не удалось отправить суперадмину: %s", e)

    await message.answer("✅ Ваше сообщение анонимно отправлено администрации.")


# --- Заглушка веб-сервера для Render ---
async def handle_ping(request):
    return web.Response(text="Bot is alive!")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()

    # Render передает свой порт через переменную окружения PORT (обычно 10000)
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)


    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )


if __name__ == "__main__":
    asyncio.run(main())