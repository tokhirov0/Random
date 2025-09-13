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
        except:
            return False
    return True

def ensure_subscription(uid):
    if not check_sub(uid):
        markup = InlineKeyboardMarkup()
        for ch in CHANNELS:
            markup.add(InlineKeyboardButton(f"➕ {ch} ga obuna bo‘lish", url=f"https://t.me/{ch[1:]}"))
        bot.send_message(uid, "❌ Botdan foydalanish uchun kanallarga obuna bo‘ling!", reply_markup=markup)
        return False
    return True

# --- Menyu ---
def menu(uid=None):
    m = InlineKeyboardMarkup()
    m.add(InlineKeyboardButton("🔎 Suhbatdosh topish", callback_data="find"))
    m.add(InlineKeyboardButton("💬 Suhbatni yopish", callback_data="stop"))
    m.add(InlineKeyboardButton("ℹ️ Bot haqida", callback_data="about"))
    if uid == ADMIN_ID:
        m.add(InlineKeyboardButton("📢 Broadcast", callback_data="broadcast"))
    return m

# --- Start komandasi ---
@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.from_user.id
    if not ensure_subscription(uid):
        return

    if uid not in users:
        users[uid] = {"step": "gender", "likes":0, "dislikes":0}

        # Inline tugma bilan boshlash
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
            bot.send_photo(CHANNELS[1], file_id, caption=caption)

            # Like/Dislike + Suhbatdosh topish
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton(f"🔎 Suhbatdosh topish", callback_data="find")
            )
            bot.send_message(uid, "Profil kanalga yuborildi!", reply_markup=markup)
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

    if data == "fill_profile":
        users[uid]["step"] = "gender"
        bot.send_message(uid, "Profilingizni to‘ldiring.\nAvval jinsingizni tanlang: Erkak / Ayol")

    elif data == "find":
        if uid in active or uid in waiting:
            bot.answer_callback_query(call.id, "Siz allaqachon suhbatdasiz yoki kutyapsiz!")
            return
        waiting.append(uid)
        bot.send_message(uid, "⏳ Suhbatdosh qidirilmoqda...")
        if len(waiting) >= 2:
            u1 = waiting.pop(0)
            u2 = waiting.pop(0)
            active[u1] = u2
            active[u2] = u1
            bot.send_message(u1, "✅ Suhbatdosh topildi!")
            bot.send_message(u2, "✅ Suhbatdosh topildi!")

    elif data == "stop":
        if uid in active:
            partner = active.pop(uid)
            active.pop(partner, None)

            # Like/Dislike + Suhbatdosh topish
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton(f"👍 Like ({users[partner].get('likes',0)})", callback_data=f"like_{partner}"),
                InlineKeyboardButton(f"👎 Dislike ({users[partner].get('dislikes',0)})", callback_data=f"dislike_{partner}")
            )
            markup.add(InlineKeyboardButton("🔎 Suhbatdosh topish", callback_data="find"))

            bot.send_message(uid, "❌ Suhbat tugatildi.", reply_markup=markup)
            bot.send_message(partner, "❌ Suhbatdosh chiqib ketdi.", reply_markup=markup)
        else:
            bot.send_message(uid, "Siz hech kim bilan suhbatda emassiz.", reply_markup=menu(uid))

    elif data.startswith("like_") or data.startswith("dislike_"):
        action, target_id = data.split("_")
        target_id = int(target_id)
        if action == "like":
            users[target_id]["likes"] = users[target_id].get("likes",0)+1
        else:
            users[target_id]["dislikes"] = users[target_id].get("dislikes",0)+1

        # Tugmani yangilash
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton(f"👍 Like ({users[target_id]['likes']})", callback_data=f"like_{target_id}"),
            InlineKeyboardButton(f"👎 Dislike ({users[target_id]['dislikes']})", callback_data=f"dislike_{target_id}")
        )
        markup.add(InlineKeyboardButton("🔎 Suhbatdosh topish", callback_data="find"))

        bot.edit_message_reply_markup(chat_id=uid, message_id=call.message.message_id, reply_markup=markup)
        bot.edit_message_reply_markup(chat_id=target_id, message_id=call.message.message_id, reply_markup=markup)

    elif data == "about":
        bot.send_message(uid, "ℹ️ RandomChat bot — anonim suhbatlar uchun yaratilgan.")

# --- Run ---
def run():
    t = threading.Thread(target=lambda: bot.infinity_polling())
    t.start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    run()
