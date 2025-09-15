import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# ====== Config ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 6733100026))
CHANNELS = ["@shaxsiy_blog1o"]
PROFILE_CHANNEL = "@anketaa_uz"

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

# ====== Ma'lumotlar ======
waiting = []
active = {}
profiles = {}
broadcast_mode = False

# ====== State-lar ======
class ProfileState(StatesGroup):
    name = State()
    gender = State()
    age = State()
    photo = State()

# ====== Menyu ======
def main_menu():
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Profil to‘ldirish", callback_data="profile")],
        [InlineKeyboardButton(text="💬 Suhbat qurish", callback_data="find")],
        [InlineKeyboardButton(text="🛑 Suhbatni yopish", callback_data="stop")],
        [InlineKeyboardButton(text="🔍 Kanal orqali topish", callback_data="search")],
        [InlineKeyboardButton(text="ℹ️ Bot haqida", callback_data="about")],
        [InlineKeyboardButton(text="⚙️ Admin panel", callback_data="admin")]
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
@dp.message(F.text == "/start")
async def start_handler(message: Message):
    if not await is_subscribed(message.from_user.id):
        markup = InlineKeyboardMarkup()
        for ch in CHANNELS:
            markup.add(InlineKeyboardButton(text=f"Obuna bo‘lish ({ch})", url=f"https://t.me/{ch.lstrip('@')}"))
        await message.answer("📢 Botdan foydalanish uchun kanallarga obuna bo‘ling!", reply_markup=markup)
        return

    await message.answer("Asosiy menyu:", reply_markup=main_menu())

# ====== Profil to‘ldirish ======
@dp.callback_query(F.data == "profile")
async def profile_start(call: CallbackQuery, state: FSMContext):
    await call.message.answer("👤 Ismingizni kiriting:")
    await state.set_state(ProfileState.name)

@dp.message(ProfileState.name, F.text)
async def set_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨 Erkak", callback_data="gender_male")],
        [InlineKeyboardButton(text="👩 Ayol", callback_data="gender_female")]
    ])
    await message.answer("Jinsingizni tanlang:", reply_markup=markup)
    await state.set_state(ProfileState.gender)

@dp.callback_query(ProfileState.gender, F.data.startswith("gender_"))
async def set_gender(call: CallbackQuery, state: FSMContext):
    gender = "Erkak" if call.data == "gender_male" else "Ayol"
    await state.update_data(gender=gender)
    await call.message.answer("📅 Yoshingizni kiriting (faqat son):")
    await state.set_state(ProfileState.age)

@dp.message(ProfileState.age, F.text)
async def set_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Faqat son kiriting!")
        return
    await state.update_data(age=message.text)
    await message.answer("📸 Rasm yuboring:")
    await state.set_state(ProfileState.photo)

@dp.message(ProfileState.photo, F.photo)
async def set_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    profiles[message.from_user.id] = {
        "name": data["name"],
        "gender": data["gender"],
        "age": data["age"],
        "photo": message.photo[-1].file_id
    }
    await message.answer("✅ Profil saqlandi!", reply_markup=main_menu())
    await state.clear()

    # Kanalga anketani yuborish
    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton(text="💬 Suhbat qurish", callback_data=f"chat_{message.from_user.id}")
    )
    await bot.send_photo(
        PROFILE_CHANNEL,
        photo=profiles[message.from_user.id]["photo"],
        caption=f"👤 {profiles[message.from_user.id]['name']}\n"
                f"Jins: {profiles[message.from_user.id]['gender']}\n"
                f"Yosh: {profiles[message.from_user.id]['age']}",
        reply_markup=markup
    )

# ====== Suhbatni boshlash/yopish, relay, admin panel ======
# (shu joylarda hammasi xuddi avvalgi kodingdagi kabi ishlaydi)

# ====== Webhook sozlash ======
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}{WEBHOOK_PATH}"

async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    await bot.session.close()   # 🔑 sessiyani yopish

async def main():
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    app.on_startup.append(lambda _: on_startup(bot))
    app.on_shutdown.append(lambda _: on_shutdown(bot))
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

if __name__ == "__main__":
    asyncio.run(main())
