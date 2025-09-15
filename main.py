import logging
import os
import threading
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from aiogram.filters import Command
from dotenv import load_dotenv
from flask import Flask

# --- Flask ---
app = Flask(__name__)

@app.route("/")
def home():
    return "🤖 Bot ishlayapti!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- Environment variables ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNELS = [os.getenv("CHANNEL_1"), os.getenv("CHANNEL_2")]
PROFILE_CHANNEL = os.getenv("PROFILE_CHANNEL")

# --- Bot ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- Database (oddiy xotirada) ---
users = {}  # user_id: {"gender":..., "age":..., "photo":..., "profile_done":bool}

# --- Menyular ---
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🗣️ Suhbat qurish")],
        [KeyboardButton(text="🔍 Qidirish"), KeyboardButton(text="❌ Suhbatni yopish")],
        [KeyboardButton(text="ℹ️ Bot haqida")],
        [KeyboardButton(text="👨‍💻 Admin panel")]
    ],
    resize_keyboard=True
)

admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="📢 Hammaga xabar yuborish")],
        [KeyboardButton(text="⬅️ Orqaga")]
    ],
    resize_keyboard=True
)

# --- Start ---
@dp.message(Command("start"))
async def start_cmd(message: Message):
    user_id = message.from_user.id

    # Majburiy obuna tekshirish
    for channel in CHANNELS:
        member = await bot.get_chat_member(channel, user_id)
        if member.status == "left":
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="📢 Kanalga obuna bo‘lish", url=f"https://t.me/{channel.strip('@')}")],
                    [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_subs")]
                ]
            )
            await message.answer("❗ Davom etish uchun quyidagi kanallarga obuna bo‘ling:", reply_markup=kb)
            return

    # Profil to‘ldirish
    if user_id not in users or not users[user_id].get("profile_done", False):
        users[user_id] = {"profile_done": False}
        await message.answer("👤 Avval profilni to‘ldiraylik.\n\n➡️ Avval jinsingizni kiriting (Erkak/Ayol).")
        return

    # Agar profil tayyor bo‘lsa
    await message.answer("🏠 Asosiy menyu", reply_markup=main_menu)

# --- Obuna qayta tekshirish ---
@dp.callback_query(F.data == "check_subs")
async def check_subs(call: CallbackQuery):
    user_id = call.from_user.id
    for channel in CHANNELS:
        member = await bot.get_chat_member(channel, user_id)
        if member.status == "left":
            await call.answer("⛔ Hali ham obuna bo‘lmadingiz!", show_alert=True)
            return
    await call.message.answer("✅ Obuna tekshirildi. Endi profilni to‘ldirishni boshlaymiz.\n\n➡️ Jinsingizni kiriting (Erkak/Ayol).")

# --- Profil: jins ---
@dp.message(F.text.in_(["Erkak", "Ayol"]))
async def set_gender(message: Message):
    user_id = message.from_user.id
    if "gender" not in users[user_id]:
        users[user_id]["gender"] = message.text
        await message.answer("📅 Yoshingizni yozing (masalan: 20)")
    else:
        await message.answer("✅ Siz allaqachon jinsni tanladingiz.")

# --- Profil: yosh ---
@dp.message(F.text.regexp(r"^\d{1,2}$"))
async def set_age(message: Message):
    user_id = message.from_user.id
    if "age" not in users[user_id]:
        users[user_id]["age"] = message.text
        await message.answer("📸 Profil rasmingizni yuboring.")
    else:
        await message.answer("✅ Siz allaqachon yoshingizni kiritgansiz.")

# --- Profil: rasm ---
@dp.message(F.photo)
async def set_photo(message: Message):
    user_id = message.from_user.id
    if "photo" not in users[user_id]:
        users[user_id]["photo"] = message.photo[-1].file_id
        users[user_id]["profile_done"] = True

        # Kanalga yuborish
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✉️ Suhbat qurish", callback_data=f"chat_{user_id}")]
            ]
        )
        caption = f"👤 Yangi foydalanuvchi anketasi:\n\n👫 Jinsi: {users[user_id]['gender']}\n📅 Yoshi: {users[user_id]['age']}"
        await bot.send_photo(PROFILE_CHANNEL, photo=users[user_id]["photo"], caption=caption, reply_markup=kb)

        await message.answer("✅ Profil muvaffaqiyatli to‘ldirildi!", reply_markup=main_menu)
    else:
        await message.answer("✅ Siz allaqachon rasm yuborgansiz.")

# --- Kanal anketasidan bosilganda ---
@dp.callback_query(F.data.regexp(r"^chat_\d+$"))
async def start_chat_request(call: CallbackQuery):
    target_id = int(call.data.split("_")[1])
    requester_id = call.from_user.id

    if target_id == requester_id:
        await call.answer("❗ O‘zingiz bilan suhbat qura olmaysiz.", show_alert=True)
        return

    await bot.send_message(target_id, "💌 Kimdir siz bilan suhbat qurmoqchi. Qabul qilasizmi?")
    await call.message.answer("✅ So‘rov yuborildi. Javobini kuting.")

# --- Admin panel ---
@dp.message(F.text == "👨‍💻 Admin panel")
async def admin_panel(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🔐 Admin paneli:", reply_markup=admin_menu)
    else:
        await message.answer("⛔ Siz admin emassiz.")

# --- Statistika ---
@dp.message(F.text == "📊 Statistika")
async def show_stats(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(f"📊 Umumiy foydalanuvchilar: {len(users)} ta")
    else:
        await message.answer("⛔ Siz admin emassiz.")

# --- Hammaga xabar ---
@dp.message(F.text == "📢 Hammaga xabar yuborish")
async def ask_broadcast(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("✍️ Xabaringizni yozing:")
        dp.message.register(broadcast_message, F.text)

async def broadcast_message(message: Message):
    if message.from_user.id == ADMIN_ID:
        text = message.text
        count = 0
        for user_id in users.keys():
            try:
                await bot.send_message(user_id, f"📢 Admin xabari:\n\n{text}")
                count += 1
            except:
                pass
        await message.answer(f"✅ Xabar {count} ta foydalanuvchiga yuborildi.", reply_markup=admin_menu)

# --- Orqaga ---
@dp.message(F.text == "⬅️ Orqaga")
async def back_main(message: Message):
    await message.answer("🏠 Asosiy menyu", reply_markup=main_menu)

# --- Oddiy menyular ---
@dp.message(F.text == "ℹ️ Bot haqida")
async def about(message: Message):
    await message.answer("ℹ️ Bu bot anonim suhbat va tanishuvlar uchun mo‘ljallangan.")

@dp.message(F.text == "❌ Suhbatni yopish")
async def close_chat(message: Message):
    await message.answer("❌ Suhbat yopildi.")

# --- Run ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Flaskni alohida oqimda ishlatish
    t = threading.Thread(target=run_flask)
    t.start()

    # Bot polling
    dp.run_polling(bot)
