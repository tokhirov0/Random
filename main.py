import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

# ===== Config =====
TOKEN = os.getenv("BOT_TOKEN")
CHANNELS = ["@shaxsiy_blog1o", "@kinoda23"]
ADMIN_ID = int(os.getenv("ADMIN_ID", 6733100026))

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# ===== Data =====
users = {}      # foydalanuvchilar ma’lumotlari
waiting = []    # kutayotganlar
active = {}     # faol suhbatlar
broadcast_mode = False

# ===== State-lar =====
class ProfileState(StatesGroup):
    name = State()
    age = State()
    gender = State()
    photo = State()

# ===== Menyu =====
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("💬 Suxbat qurish"), KeyboardButton("❌ Suxbat yopish")],
            [KeyboardButton("👤 Profil to‘ldirish")],
            [KeyboardButton("ℹ️ Bot haqida"), KeyboardButton("📢 Kanalimizdan suxbatdosh topish")],
            [KeyboardButton("⚙️ Admin panel")]
        ],
        resize_keyboard=True
    )

# ===== Kanal obuna tekshiruv =====
async def is_subscribed(user_id):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# ===== Start =====
@dp.message(F.text == "/start")
async def start_handler(message: Message):
    if not await is_subscribed(message.from_user.id):
        btns = [[KeyboardButton(f"Obuna bo‘lish: {ch}")] for ch in CHANNELS]
        markup = ReplyKeyboardMarkup(keyboard=btns, resize_keyboard=True)
        await message.answer("📢 Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling!", reply_markup=markup)
        return
    await message.answer("Asosiy menyu:", reply_markup=main_menu())

# ===== Profil to‘ldirish =====
@dp.message(F.text == "👤 Profil to‘ldirish")
async def fill_profile(message: Message, state: FSMContext):
    await message.answer("✍️ Ismingizni kiriting:")
    await state.set_state(ProfileState.name)

@dp.message(ProfileState.name, F.text)
async def set_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("📅 Yoshingizni kiriting:")
    await state.set_state(ProfileState.age)

@dp.message(ProfileState.age, F.text)
async def set_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Faqat son kiriting!")
        return
    await state.update_data(age=message.text)
    await message.answer("👨 Erkak yoki 👩 Ayol?")
    await state.set_state(ProfileState.gender)

@dp.message(ProfileState.gender, F.text)
async def set_gender(message: Message, state: FSMContext):
    gender = message.text.strip()
    if gender not in ["Erkak", "Ayol", "👨 Erkak", "👩 Ayol"]:
        await message.answer("❌ 'Erkak' yoki 'Ayol' deb yozing!")
        return
    await state.update_data(gender=gender.replace("👨 ", "").replace("👩 ", ""))
    await message.answer("📸 Rasm yuboring:")
    await state.set_state(ProfileState.photo)

@dp.message(ProfileState.photo, F.photo)
async def set_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    users[message.from_user.id] = {
        "name": data["name"],
        "age": data["age"],
        "gender": data["gender"],
        "photo": message.photo[-1].file_id
    }
    await message.answer("✅ Profil to‘ldirildi!", reply_markup=main_menu())
    await state.clear()

# ===== Suxbat qurish =====
@dp.message(F.text == "💬 Suxbat qurish")
async def find_partner(message: Message):
    user_id = message.from_user.id
    if user_id in active:
        await message.answer("⚠️ Siz allaqachon suhbatdasiz!")
        return
    if waiting and waiting[0] != user_id:
        partner_id = waiting.pop(0)
        active[user_id] = partner_id
        active[partner_id] = user_id
        await bot.send_message(user_id, "✅ Suhbat boshlandi!")
        await bot.send_message(partner_id, "✅ Suhbat boshlandi!")
    else:
        waiting.append(user_id)
        await message.answer("⌛ Suxbatdosh qidirilmoqda...")

# ===== Suxbat yopish =====
@dp.message(F.text == "❌ Suxbat yopish")
async def stop_chat(message: Message):
    user_id = message.from_user.id
    if user_id not in active:
        await message.answer("❌ Siz suhbatda emassiz.")
        return
    partner_id = active[user_id]
    del active[user_id]
    if partner_id in active:
        del active[partner_id]
    await bot.send_message(user_id, "🛑 Suhbat tugatildi.", reply_markup=main_menu())
    await bot.send_message(partner_id, "🛑 Suhbat tugatildi.", reply_markup=main_menu())

# ===== Xabar uzatish =====
@dp.message(F.text)
async def relay_message(message: Message):
    user_id = message.from_user.id
    if user_id in active:
        partner_id = active[user_id]
        try:
            await bot.send_message(partner_id, message.text)
        except:
            await message.answer("⚠️ Xabar yuborilmadi.")

# ===== Bot haqida =====
@dp.message(F.text == "ℹ️ Bot haqida")
async def about_bot(message: Message):
    text = (
        "🤖 Bu bot orqali siz anonim tarzda yangi do‘stlar bilan suxbatlasha olasiz.\n\n"
        "📌 Funksiyalar:\n"
        "– 💬 Suxbat qurish / yopish\n"
        "– 👤 Profil to‘ldirish\n"
        "– 📢 Kanal orqali suxbatdosh topish\n\n"
        "Dasturchi: @tokhirov_0"
    )
    await message.answer(text)

# ===== Kanal orqali suxbatdosh =====
@dp.message(F.text == "📢 Kanalimizdan suxbatdosh topish")
async def from_channel(message: Message):
    text = "📢 Kanalimizga qo‘shiling:\n👉 @shaxsiy_blog1o\n👉 @kinoda23\nSo‘ngra /start tugmasini bosing ✅"
    await message.answer(text)

# ===== Admin panel =====
@dp.message(F.text == "⚙️ Admin panel")
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Siz admin emassiz.")
        return
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("📊 Statistika"), KeyboardButton("📨 Hammaga xabar yuborish")],
            [KeyboardButton("⬅️ Ortga")]
        ],
        resize_keyboard=True
    )
    await message.answer("⚙️ Admin panel:", reply_markup=markup)

@dp.message(F.text == "📊 Statistika")
async def stats(message: Message):
    if message.from_user.id == ADMIN_ID:
        total = len(users)
        active_chats = len(active) // 2
        await message.answer(f"👥 Umumiy foydalanuvchilar: {total}\n💬 Faol suhbatlar: {active_chats}")

@dp.message(F.text == "📨 Hammaga xabar yuborish")
async def broadcast(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.set_state("broadcast")
    await message.answer("✍️ Hammaga yuboriladigan xabarni kiriting:")

@dp.message(F.text, state="broadcast")
async def broadcast_message(message: Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        sent = 0
        for uid in users.keys():
            try:
                await bot.send_message(uid, f"📢 Admin xabari:\n\n{message.text}")
                sent += 1
            except:
                pass
        await message.answer(f"✅ {sent} ta foydalanuvchiga yuborildi.")
    await state.clear()

# ===== Webhook =====
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}{WEBHOOK_PATH}"

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(app):
    await bot.delete_webhook()

def main():
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

if __name__ == "__main__":
    main()
