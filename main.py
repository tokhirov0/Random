import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# ====== Config ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 6733100026))
CHANNELS = ["@shaxsiy_blog1o", "@kinoda23"]
PROFILE_CHANNEL = "@anketaa_uz"
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}{WEBHOOK_PATH}"
PORT = int(os.getenv("PORT", 10000))

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# ====== Ma'lumotlar ======
waiting = []
active = {}
profiles = {}
broadcast_mode = False

# ====== States ======
class ProfileState(StatesGroup):
    name = State()
    gender = State()
    age = State()
    photo = State()

# ====== Menyu ======
def main_menu():
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="👤 Profil to‘ldirish", callback_data="profile")],
        [types.InlineKeyboardButton(text="💬 Suhbat qurish", callback_data="find")],
        [types.InlineKeyboardButton(text="🛑 Suhbatni yopish", callback_data="stop")],
        [types.InlineKeyboardButton(text="🔍 Kanal orqali topish", callback_data="search")],
        [types.InlineKeyboardButton(text="ℹ️ Bot haqida", callback_data="about")],
        [types.InlineKeyboardButton(text="⚙️ Admin panel", callback_data="admin")]
    ])
    return markup

# ====== Kanal obuna tekshiruvi ======
async def is_subscribed(user_id):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# ====== Handlers (profil, chat, admin, broadcast va h.k.) ======
# Shu yerga sizning barcha callback va message handler-lar bo‘ladi
# (Avvalgi polling kodidan olingan, faqat polling o‘rniga webhook ishlatiladi)

# ====== Webhook sozlash ======
async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dp):
    await bot.delete_webhook()
    await bot.session.close()

async def init_app():
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    app.on_startup.append(lambda _: on_startup(dp))
    app.on_shutdown.append(lambda _: on_shutdown(dp))
    return app

if __name__ == "__main__":
    app = asyncio.run(init_app())
    web.run_app(app, host="0.0.0.0", port=PORT)
