import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

TOKEN = "8309762183:AAF8gEz6C6w7XpKUsy_U2yqi6kBqhG-gohE"
ADMIN_ID = 6733100026
CHANNELS = ["@anketaa_uz", "@shaxsiy_blog1o"]

bot = Bot(token=TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

# Userlar bazasi (oddiy dict orqali)
users = {}
profiles = {}
waiting = set()
active_chats = {}

# ======= Kanal tekshiruvi =======
async def check_sub(user_id):
    for ch in CHANNELS:
        chat = await bot.get_chat_member(ch, user_id)
        if chat.status == "left":
            return False
    return True

def sub_buttons():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga obuna boʻlish", url=f"https://t.me/{ch[1:]}")] for ch in CHANNELS
    ] + [[InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")]])
    return kb

# ======= Start =======
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if not await check_sub(message.from_user.id):
        await message.answer("❗️ Botdan foydalanish uchun kanallarga obuna boʻling:", reply_markup=sub_buttons())
        return
    if message.from_user.id not in profiles:
        await message.answer("👤 Profilingizni toʻldiring.\n\nIsmingizni yuboring:")
        users[message.from_user.id] = {"step": "name"}
    else:
        await message.answer("🔹 Siz allaqachon roʻyxatdan oʻtgansiz!", reply_markup=main_menu())

# ======= Callback check_sub =======
@dp.callback_query(lambda c: c.data == "check_sub")
async def check_subscription(callback: types.CallbackQuery):
    if await check_sub(callback.from_user.id):
        await callback.message.answer("✅ Obuna tasdiqlandi. Endi profilni toʻldiring.\n\nIsmingizni yuboring:")
        users[callback.from_user.id] = {"step": "name"}
    else:
        await callback.message.answer("❗️ Obuna boʻlmagansiz!", reply_markup=sub_buttons())

# ======= Profil toʻldirish =======
@dp.message()
async def profile_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id in users:
        step = users[user_id]["step"]

        if step == "name":
            users[user_id]["name"] = message.text
            users[user_id]["step"] = "gender"
            await message.answer("👫 Jinsingizni tanlang:", reply_markup=gender_kb())

        elif step == "gender":
            if message.text not in ["Erkak", "Ayol"]:
                await message.answer("❗️ Faqat 'Erkak' yoki 'Ayol' deb yuboring")
                return
            users[user_id]["gender"] = message.text
            users[user_id]["step"] = "age"
            await message.answer("📅 Yosh kiriting:")

        elif step == "age":
            if not message.text.isdigit():
                await message.answer("❗️ Yosh faqat son boʻlishi kerak")
                return
            users[user_id]["age"] = message.text
            users[user_id]["step"] = "photo"
            await message.answer("📸 Profil rasmingizni yuboring:")

        elif step == "photo":
            if not message.photo:
                await message.answer("❗️ Rasm yuboring")
                return
            photo_id = message.photo[-1].file_id
            profiles[user_id] = {
                "name": users[user_id]["name"],
                "gender": users[user_id]["gender"],
                "age": users[user_id]["age"],
                "photo": photo_id
            }
            del users[user_id]
            await message.answer("✅ Profilingiz saqlandi!", reply_markup=main_menu())

            # Kanalga chiqarish
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💬 Suhbat qurish", callback_data=f"chat_{user_id}")]
            ])
            await bot.send_photo(CHANNELS[0], photo=photo_id,
                                 caption=f"👤 {profiles[user_id]['name']}\n"
                                         f"🧑‍🦱 Jins: {profiles[user_id]['gender']}\n"
                                         f"📅 Yosh: {profiles[user_id]['age']}",
                                 reply_markup=kb)

# ======= Inline chat bosilganda =======
@dp.callback_query(lambda c: c.data.startswith("chat_"))
async def request_chat(callback: types.CallbackQuery):
    target_id = int(callback.data.split("_")[1])
    from_id = callback.from_user.id
    if target_id not in profiles:
        await callback.answer("❗️ Foydalanuvchi mavjud emas", show_alert=True)
        return
    await bot.send_message(target_id, f"📩 Siz bilan {callback.from_user.full_name} suhbat qurmoqchi.\n"
                                      f"✅ Qabul qilish uchun /accept yuboring.")
    users[target_id] = {"step": "accept", "partner": from_id}
    await callback.answer("✅ Soʻrov yuborildi", show_alert=True)

# ======= Accept =======
@dp.message(Command("accept"))
async def accept_chat(message: types.Message):
    user_id = message.from_user.id
    if user_id in users and users[user_id]["step"] == "accept":
        partner = users[user_id]["partner"]
        active_chats[user_id] = partner
        active_chats[partner] = user_id
        await bot.send_message(user_id, "✅ Suhbat boshlandi!\n❌ Tugatish uchun /stop")
        await bot.send_message(partner, "✅ Suhbat boshlandi!\n❌ Tugatish uchun /stop")
        del users[user_id]

# ======= Stop =======
@dp.message(Command("stop"))
async def stop_chat(message: types.Message):
    user_id = message.from_user.id
    if user_id in active_chats:
        partner = active_chats[user_id]
        await bot.send_message(partner, "❌ Suhbat tugadi")
        await bot.send_message(user_id, "❌ Suhbat tugadi")
        del active_chats[partner]
        del active_chats[user_id]

# ======= Forward messages in chat =======
@dp.message()
async def chat_forward(message: types.Message):
    user_id = message.from_user.id
    if user_id in active_chats:
        partner = active_chats[user_id]
        if message.text:
            await bot.send_message(partner, message.text)
        elif message.photo:
            await bot.send_photo(partner, message.photo[-1].file_id, caption=message.caption if message.caption else "")

# ======= Admin panel =======
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="📢 Xabar yuborish")]
    ], resize_keyboard=True)
    await message.answer("⚙️ Admin panel", reply_markup=kb)

@dp.message(lambda m: m.text == "📊 Statistika" and m.from_user.id == ADMIN_ID)
async def stats(message: types.Message):
    await message.answer(f"👥 Foydalanuvchilar soni: {len(profiles)}")

@dp.message(lambda m: m.text == "📢 Xabar yuborish" and m.from_user.id == ADMIN_ID)
async def broadcast_start(message: types.Message):
    users[message.from_user.id] = {"step": "broadcast"}
    await message.answer("✍️ Xabar matnini yuboring:")

@dp.message()
async def broadcast(message: types.Message):
    if message.from_user.id in users and users[message.from_user.id]["step"] == "broadcast":
        for uid in profiles.keys():
            try:
                await bot.send_message(uid, message.text)
            except:
                pass
        await message.answer("✅ Xabar yuborildi")
        del users[message.from_user.id]

# ======= Helper menu =======
def main_menu():
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🔍 Qidirish")],
        [KeyboardButton(text="💬 Suhbat qurish"), KeyboardButton(text="❌ Suhbatni yopish")],
        [KeyboardButton(text="ℹ️ Bot haqida")]
    ], resize_keyboard=True)
    return kb

def gender_kb():
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Erkak"), KeyboardButton(text="Ayol")]
    ], resize_keyboard=True)
    return kb

# ======= Run =======
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
