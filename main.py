import os
import threading
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask

# --- Environment Variables ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNELS = os.getenv("CHANNELS", "").split(",")  # '@anketaa_uz,@shaxsiy_blog1o'

bot = telebot.TeleBot(TOKEN)
waiting = []
active = {}
profiles = {}
users = set()

# --- Flask (Render portni talab qiladi) ---
app = Flask(__name__)

@app.route("/")
def home():
    return "RandomChat Bot is running on Render!"

# --- Asosiy menyu ---
def main_menu(user_id=None):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🔎 Suhbatdosh topish", callback_data="find"),
        InlineKeyboardButton("🛑 Suhbatni to'xtatish", callback_data="stop"),
        InlineKeyboardButton("ℹ️ Bot haqida", callback_data="about"),
    )
    if user_id == ADMIN_ID:  # faqat admin ko‘radi
        markup.add(InlineKeyboardButton("⚙️ Admin panel", callback_data="admin"))
    return markup

# --- Kanal obunasi tekshirish ---
def is_subscribed(user_id):
    try:
        for channel in CHANNELS:
            if not channel:
                continue
            member = bot.get_chat_member(channel.strip(), user_id)
            if member.status in ['member', 'administrator', 'creator']:
                continue
            else:
                return False
        return True
    except Exception:
        return False

# --- Start komandasi ---
@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    users.add(user_id)

    if not is_subscribed(user_id):
        markup = InlineKeyboardMarkup()
        for channel in CHANNELS:
            if channel:
                markup.add(InlineKeyboardButton(f"📢 {channel}", url=f"https://t.me/{channel.lstrip('@')}"))
        bot.send_message(user_id, "❗ Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:", reply_markup=markup)
        return

    # Profil ma’lumotlari yo‘q bo‘lsa, to‘ldirishni so‘raymiz
    if user_id not in profiles:
        bot.send_message(user_id, "👤 Avval profil ma’lumotlaringizni to‘ldiring.")
        bot.send_message(user_id, "Jinsingizni kiriting (Erkak/Ayol):")
        bot.register_next_step_handler(message, process_gender)
    else:
        bot.send_message(user_id, "Assalomu alaykum! Xush kelibsiz!\nQuyidagi menyudan foydalaning 👇", reply_markup=main_menu(user_id))

# --- Profil to‘ldirish ---
def process_gender(message):
    user_id = message.from_user.id
    gender = message.text.strip().lower()
    profiles[user_id] = {"gender": gender}
    bot.send_message(user_id, "✍️ Yoshingizni kiriting:")
    bot.register_next_step_handler(message, process_age)

def process_age(message):
    user_id = message.from_user.id
    age = message.text.strip()
    profiles[user_id]["age"] = age
    bot.send_message(user_id, "📸 Rasm yuboring:")
    bot.register_next_step_handler(message, process_photo)

def process_photo(message):
    user_id = message.from_user.id
    if not message.photo:
        bot.send_message(user_id, "❌ Rasm yuboring!")
        return
    photo_id = message.photo[-1].file_id
    profiles[user_id]["photo"] = photo_id

    # Kanalga anketa yuboriladi
    caption = f"👤 Yangi anketa:\n\n👥 Jinsi: {profiles[user_id]['gender']}\n🎂 Yoshi: {profiles[user_id]['age']}"
    for channel in CHANNELS:
        if channel:
            bot.send_photo(channel, photo_id, caption=caption)

    bot.send_message(user_id, "✅ Profilingiz saqlandi!", reply_markup=main_menu(user_id))

# --- Callback tugmalar ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id

    if call.data == "find":
        if user_id in waiting or user_id in active:
            bot.answer_callback_query(call.id, "Siz allaqachon navbattasiz yoki suhbatdasiz!")
            return
        waiting.append(user_id)
        bot.send_message(user_id, "⏳ Siz navbatga qo‘shildingiz. Suhbatdosh topilmoqda...")

        if len(waiting) >= 2:
            user1 = waiting.pop(0)
            user2 = waiting.pop(0)
            active[user1] = user2
            active[user2] = user1
            bot.send_message(user1, "✅ Suhbatdosh topildi! Suhbatni boshlang.")
            bot.send_message(user2, "✅ Suhbatdosh topildi! Suhbatni boshlang.")

    elif call.data == "stop":
        if user_id in active:
            partner_id = active.pop(user_id)
            active.pop(partner_id, None)
            bot.send_message(user_id, "❌ Suhbat to‘xtatildi.", reply_markup=main_menu(user_id))
            bot.send_message(partner_id, "❌ Suhbatdosh suhbatni to‘xtatdi.", reply_markup=main_menu(partner_id))
        else:
            bot.send_message(user_id, "Siz hozircha hech kim bilan suhbatda emassiz.", reply_markup=main_menu(user_id))

    elif call.data == "about":
        bot.send_message(user_id, "🤖 Bu anonim RandomChat bot.\n👥 Suhbatdoshingizni topib, bemalol muloqot qiling!")

    elif call.data == "admin" and user_id == ADMIN_ID:
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("📊 Statistika", callback_data="stats"),
            InlineKeyboardButton("📢 Hamma foydalanuvchilarga xabar yuborish", callback_data="broadcast")
        )
        bot.send_message(user_id, "⚙️ Admin paneliga xush kelibsiz:", reply_markup=markup)

    elif call.data == "stats" and user_id == ADMIN_ID:
        bot.send_message(user_id, f"📊 Bot foydalanuvchilari soni: {len(users)} ta")

    elif call.data == "broadcast" and user_id == ADMIN_ID:
        bot.send_message(user_id, "✍️ Hamma foydalanuvchilarga yuboriladigan xabar matnini yozing:")
        bot.register_next_step_handler(call.message, process_broadcast)

# --- Admin broadcast ---
def process_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text
    count = 0
    for user_id in list(users):
        try:
            bot.send_message(user_id, text)
            count += 1
        except:
            pass
    bot.send_message(ADMIN_ID, f"📢 Xabar {count} ta foydalanuvchiga yuborildi.")

# --- Xabarlarni uzatish ---
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo'])
def relay_message(message):
    user_id = message.from_user.id
    if user_id in active:
        partner_id = active[user_id]
        try:
            if message.text:
                bot.send_message(partner_id, message.text)
            elif message.photo:
                bot.send_photo(partner_id, message.photo[-1].file_id, caption=message.caption or "")
        except Exception:
            bot.send_message(user_id, "⚠️ Xabar yuborib bo‘lmadi.")
    else:
        bot.send_message(user_id, "Siz hozircha suhbatda emassiz.\nSuhbatdosh topish uchun tugmani bosing.", reply_markup=main_menu(user_id))

# --- Botni boshqa oqimda ishga tushirish ---
def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    t = threading.Thread(target=run_bot)
    t.start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
