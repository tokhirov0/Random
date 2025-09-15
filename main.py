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

# ====== Kanal orqali suhbat ======
@dp.callback_query(F.data.startswith("chat_"))
async def start_chat_request(call: CallbackQuery):
    target_id = int(call.data.split("_")[1])
    requester = call.from_user.id

    if target_id not in profiles:
        await call.message.answer("❌ Ushbu foydalanuvchi mavjud emas.")
        return

    await bot.send_message(target_id, "💬 Kimdir siz bilan suhbat qurmoqchi. Qabul qilasizmi?",
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                               [InlineKeyboardButton(text="✅ Ha", callback_data=f"accept_{requester}")],
                               [InlineKeyboardButton(text="❌ Yo‘q", callback_data="reject")]
                           ]))

@dp.callback_query(F.data.startswith("accept_"))
async def accept_chat(call: CallbackQuery):
    partner_id = int(call.data.split("_")[1])
    user_id = call.from_user.id

    active[user_id] = partner_id
    active[partner_id] = user_id

    await bot.send_message(user_id, "✅ Suhbat boshlandi!")
    await bot.send_message(partner_id, "✅ Suhbat boshlandi!")

@dp.callback_query(F.data == "reject")
async def reject_chat(call: CallbackQuery):
    await call.message.answer("❌ Siz suhbatni rad etdingiz.")

# ====== Random suhbat ======
@dp.callback_query(F.data == "find")
async def find_partner(call: CallbackQuery):
    user_id = call.from_user.id

    if user_id in active:
        await call.message.answer("⚠️ Siz allaqachon suhbatdasiz!")
        return

    if waiting and waiting[0] != user_id:
        partner_id = waiting.pop(0)
        active[user_id] = partner_id
        active[partner_id] = user_id
        await bot.send_message(user_id, "✅ Suhbat boshlandi!")
        await bot.send_message(partner_id, "✅ Suhbat boshlandi!")
    else:
        waiting.append(user_id)
        await call.message.answer("⌛ Suhbatdosh qidirilmoqda...")

# ====== Suhbatni yopish ======
@dp.callback_query(F.data == "stop")
async def stop_chat(call: CallbackQuery):
    user_id = call.from_user.id

    if user_id not in active:
        await call.message.answer("❌ Siz hozircha suhbatda emassiz.")
        return

    partner_id = active[user_id]
    del active[user_id]
    if partner_id in active:
        del active[partner_id]

    await bot.send_message(user_id, "🛑 Suhbat tugatildi.", reply_markup=main_menu())
    await bot.send_message(partner_id, "🛑 Suhbat tugatildi.", reply_markup=main_menu())

# ====== Xabarlarni uzatish ======
@dp.message(F.text)
async def relay_message(message: Message):
    global broadcast_mode
    user_id = message.from_user.id

    # Admin broadcast
    if broadcast_mode and user_id == ADMIN_ID:
        count = 0
        for uid in profiles.keys():
            try:
                await bot.send_message(uid, f"📢 Admin xabari:\n\n{message.text}")
                count += 1
            except:
                pass
        await message.answer(f"✅ {count} ta foydalanuvchiga yuborildi.")
        broadcast_mode = False
        return

    # Oddiy xabar
    if user_id in active:
        partner_id = active[user_id]
        try:
            await bot.send_message(partner_id, message.text)
        except:
            await message.answer("⚠️ Xabar yuborilmadi.")
    else:
        await message.answer("Siz hozircha suhbatda emassiz.", reply_markup=main_menu())

# ====== Bot haqida ======
@dp.callback_query(F.data == "about")
async def about(call: CallbackQuery):
    await call.message.answer("ℹ️ Bu anonim suhbat botidir.\n\n👤 Profil to‘ldiring va suhbat boshlang!")

# ====== Admin panel ======
@dp.callback_query(F.data == "admin")
async def admin_panel(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.message.answer("❌ Siz admin emassiz!")
        return
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="stats")],
        [InlineKeyboardButton(text="📢 Hammaga xabar", callback_data="broadcast")]
    ])
    await call.message.answer("⚙️ Admin panel:", reply_markup=markup)

@dp.callback_query(F.data == "stats")
async def stats(call: CallbackQuery):
    if call.from_user.id == ADMIN_ID:
        await call.message.answer(f"👥 Umumiy foydalanuvchilar: {len(profiles)}")

@dp.callback_query(F.data == "broadcast")
async def broadcast_start(call: CallbackQuery):
    global broadcast_mode
    if call.from_user.id == ADMIN_ID:
        broadcast_mode = True
        await call.message.answer("📢 Hammaga yuboriladigan xabarni kiriting:")

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
