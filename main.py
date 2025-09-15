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

# ====== Start ======
@dp.message(types.filters.Text(equals="/start"))
async def start_handler(message: types.Message):
    if not await is_subscribed(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        for ch in CHANNELS:
            markup.add(types.InlineKeyboardButton(text=f"Obuna bo‘lish ({ch})", url=f"https://t.me/{ch.lstrip('@')}"))
        await message.answer("📢 Botdan foydalanish uchun barcha kanallarga obuna bo‘ling!", reply_markup=markup)
        return
    await message.answer("Asosiy menyu:", reply_markup=main_menu())

# ====== Profil to‘ldirish ======
@dp.callback_query(types.filters.Text(equals="profile"))
async def profile_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("👤 Ismingizni kiriting:")
    await state.set_state(ProfileState.name)

@dp.message(ProfileState.name, types.filters.Text())
async def set_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="👨 Erkak", callback_data="gender_male")],
        [types.InlineKeyboardButton(text="👩 Ayol", callback_data="gender_female")]
    ])
    await message.answer("Jinsingizni tanlang:", reply_markup=markup)
    await state.set_state(ProfileState.gender)

@dp.callback_query(types.filters.Text(startswith="gender_"))
async def set_gender(call: types.CallbackQuery, state: FSMContext):
    gender = "Erkak" if call.data == "gender_male" else "Ayol"
    await state.update_data(gender=gender)
    await call.message.answer("📅 Yoshingizni kiriting (faqat son):")
    await state.set_state(ProfileState.age)

@dp.message(ProfileState.age, types.filters.Text())
async def set_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Faqat son kiriting!")
        return
    await state.update_data(age=message.text)
    await message.answer("📸 Rasm yuboring:")
    await state.set_state(ProfileState.photo)

@dp.message(ProfileState.photo, types.filters.Photo())
async def set_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    profiles[message.from_user.id] = {
        "name": data["name"],
        "gender": data["gender"],
        "age": data["age"],
        "photo": message.photo[-1].file_id
    }
    await message.answer("✅ Profil saqlandi!", reply_markup=main_menu())
    await state.clear()

    markup = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton(text="💬 Suhbat qurish", callback_data=f"chat_{message.from_user.id}")
    )
    await bot.send_photo(
        PROFILE_CHANNEL,
        photo=profiles[message.from_user.id]["photo"],
        caption=f"👤 {profiles[message.from_user.id]['name']}\n"
                f"Jins: {profiles[message.from_user.id]['gender']}\n"
                f"Yosh: {profiles[message.from_user.id]['age']}",
        reply_markup=markup
    )

# ====== Shu yerga boshqa barcha callback va message handler-lar (chat, admin, broadcast) ======
# Polling handlerlar webhook bilan ishlash uchun moslashtiriladi

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
