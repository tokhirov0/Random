import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
import threading

# --- ENV sozlamalar ---
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("❌ BOT TOKEN Environment Variables da topilmadi!")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 6733100026))
CHANNELS = ["@shaxsiy_blog1o", "@anketaa_uz"]

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- Ma'lumotlar ---
users = {}
waiting = []
active = {}

# --- Render uchun test route ---
@app.route("/")
def home():
    return "RandomChat Bot is running!"

# --- Obuna tekshirish ---
def check_sub(user_id):
    for ch in CHANNELS:
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except Exception as e:
            print(f"Xato: {e}")
            return False
    return True

def ensure_subscription(uid):
    if not check_sub(uid):
        channels_list = [f"{i+1} - {ch}" for i, ch in enumerate(CHANNELS)]
        message = "❌ Kechirasiz, botimizdan foydalanishingizdan oldin quyidagi kanallarga a'zo bo'lishingiz kerak:\n"
        markup = InlineKeyboardMarkup()
        for channel in channels_list:
            markup.add(InlineKeyboardButton(channel, url=f"https://t.me/{channel[4:]}"))
        markup.add(InlineKeyboardButton("✅ Tasdiqlash", callback_data="check_subscription"))
        bot.send_message(uid, message, reply_markup=markup)
        return False
    return True

# --- Inline Menyu ---
def menu(uid=None):
    m = InlineKeyboardMarkup()
    m.add(InlineKeyboardButton("🔎 Suhbat qurish", callback_data="find"))
    m.add(InlineKeyboardButton("💬 Suhbatni yopish", callback_data="stop"))
    m.add(InlineKeyboardButton("ℹ️ Bot haqida ma'lumot", callback_data="about"))
    m.add(InlineKeyboardButton("📢 Kanaldan suhbatdosh topish", callback_data="channel_find"))
    if uid == ADMIN_ID:
        m.add(InlineKeyboardButton("👤 Admin paneli", callback_data="admin_panel"))
    return m

# --- Admin paneli ---
def admin_menu():
    m = InlineKeyboardMarkup()
    m.add(InlineKeyboardButton("📢 Hammaga xabar yuborish", callback_data="broadcast"))
    m.add(InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_menu"))
    return m

# --- Start komandasi ---
@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.from_user.id
    if not ensure_subscription(uid):
        return

    if uid not in users:
        users[uid] = {"step": "gender"}
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📝 Profilni to‘ldirish", callback_data="fill_profile"))
        bot.send_message(uid, "✅ Obuna bo‘ldingiz! Endi profilni to‘ldiring.", reply_markup=markup)
    else:
        bot.send_message(uid, "Asosiy menyu:", reply_markup=menu(uid))

# --- Profil handler ---
@bot.message_handler(func=lambda m: True, content_types=["text", "photo"])
def profile_handler(msg):
    uid = msg.from_user.id
    if uid not in users:
        return
    step = users[uid].get("step")
    if step == "gender":
        if msg.text.lower() in ["erkak", "1"]:
            users[uid]["gender"] = "Erkak"
        elif msg.text.lower() in ["ayol", "2"]:
            users[uid]["gender"] = "Ayol"
        else:
            bot.send_message(uid, "Faqat 'Erkak' yoki 'Ayol' deb yozing.")
            return
        users[uid]["step"] = "age"
        bot.send_message(uid, "✅ Jins saqlandi. Endi yoshingizni kiriting:")

    elif step == "age":
        if msg.text.isdigit():
            users[uid]["age"] = msg.text
            users[uid]["step"] = "photo"
            bot.send_message(uid, "✅ Yosh saqlandi. Endi rasmingizni yuboring:")
        else:
            bot.send_message(uid, "Iltimos, yoshni raqamda kiriting.")

    elif step == "photo":
        if msg.content_type == "photo":
            file_id = msg.photo[-1].file_id
            users[uid]["photo"] = file_id
            users[uid]["step"] = "done"
            bot.send_message(uid, "✅ Rasm qabul qilindi. Profilingiz to‘liq!")

            # Kanalga yuborish
            caption = f"👤 Yangi profil:\n👥 Jinsi: {users[uid]['gender']}\n🎂 Yosh: {users[uid]['age']}"
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔎 Suhbat qurish", callback_data="find"))
            bot.send_photo(CHANNELS[1], file_id, caption=caption, reply_markup=markup)

            bot.send_message(uid, "Profil kanalga yuborildi!", reply_markup=menu(uid))
        else:
            bot.send_message(uid, "Iltimos, rasm yuboring.")

    elif uid in active:
        partner = active[uid]
        if msg.content_type == "text":
            bot.send_message(partner, msg.text)
        elif msg.content_type == "photo":
            bot.send_photo(partner, msg.photo[-1].file_id)

# --- Callback handler ---
@bot.callback_query_handler(func=lambda c: True)
def cb(call):
    uid = call.from_user.id
    data = call.data

    if data == "check_subscription":
        if check_sub(uid):
            bot.edit_message_text("✅ Obuna tekshiruvi muvaffaqiyatli! Endi botdan foydalanishingiz mumkin.", chat_id=uid, message_id=call.message.message_id, reply_markup=menu(uid))
        else:
            bot.answer_callback_query(call.id, "❌ Hali barcha kanallarga obuna bo'lmadingiz!")

    elif data == "fill_profile":
        users[uid]["step"] = "gender"
        bot.send_message(uid, "Profilingizni to‘ldiring.\nAvval jinsingizni tanlang: Erkak / Ayol", reply_markup=menu(uid))

    elif data == "find":
        if uid in active or uid in waiting:
            bot.answer_callback_query(call.id, "Siz allaqachon suhbatdasiz yoki kutyapsiz!")
            return
        waiting.append(uid)
        bot.send_message(uid, "⏳ Suhbatdosh qidirilmoqda...", reply_markup=menu(uid))
        if len(waiting) >= 2:
            u1 = waiting.pop(0)
            u2 = waiting.pop(0)
            active[u1] = u2
            active[u2] = u1
            bot.send_message(u1, "✅ Suhbatdosh topildi!", reply_markup=menu(u1))
            bot.send_message(u2, "✅ Suhbatdosh topildi!", reply_markup=menu(u2))

    elif data == "stop":
        if uid in active:
            partner = active.pop(uid)
            active.pop(partner, None)

            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔎 Suhbat qurish", callback_data="find"))

            bot.send_message(uid, "❌ Suhbat tugatildi.", reply_markup=markup)
            bot.send_message(partner, "❌ Suhbatdosh chiqib ketdi.", reply_markup=markup)
        else:
            bot.send_message(uid, "Siz hech kim bilan suhbatda emassiz.", reply_markup=menu(uid))

    elif data == "about":
        bot.send_message(uid, "ℹ️ RandomChat bot — anonim suhbatlar uchun yaratilgan.", reply_markup=menu(uid))

    elif data == "channel_find":
        bot.send_message(uid, f"📢 Suhbatdoshni kanal orqali toping: {CHANNELS[1]}", reply_markup=menu(uid))

    elif data == "admin_panel":
        if uid == ADMIN_ID:
            bot.send_message(uid, "Admin paneli:", reply_markup=admin_menu())
        else:
            bot.answer_callback_query(call.id, "Siz admin emassiz!")

    elif data == "broadcast":
        if uid == ADMIN_ID:
            bot.send_message(uid, "Xabarni kiriting:", reply_markup=admin_menu())
            bot.register_next_step_handler(call.message, send_broadcast)

    elif data == "back_to_menu":
        bot.edit_message_text("Asosiy menyu:", chat_id=uid, message_id=call.message.message_id, reply_markup=menu(uid))

# --- Broadcast funksiyasi ---
def send_broadcast(msg):
    text = msg.text
    for user_id in users:
        try:
            bot.send_message(user_id, text)
        except:
            continue
    bot.send_message(msg.from_user.id, "✅ Xabar yuborildi!", reply_markup=menu(msg.from_user.id))

# --- Run ---
def run():
    t = threading.Thread(target=lambda: bot.infinity_polling())
    t.start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    run()
