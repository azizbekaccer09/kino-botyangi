import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import telebot
from telebot import types
from config import BOT_TOKEN, ADMIN_IDS
import database as db


# ================= RENDER UCHUN "TIRIK" SERVER =================
# Render Free Web Service portni tinglashni talab qiladi va
# UptimeRobot shu manzilga so'rov yuborib botni uyg'oq tutadi.

class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive")

    def log_message(self, format, *args):
        pass  # konsolni ping loglari bilan to'ldirmaslik uchun


def run_ping_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), PingHandler)
    server.serve_forever()


threading.Thread(target=run_ping_server, daemon=True).start()

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
db.init_db()
db.seed_admins(ADMIN_IDS)  # config.py dagi boshlang'ich adminlarni bazaga kiritish

# Foydalanuvchi holatini vaqtinchalik saqlash uchun (kod kutish, video kutish va h.k.)
user_state = {}          # user_id -> "waiting_code" | "waiting_video" | "waiting_movie_code" | "waiting_delete_code"
pending_upload = {}      # user_id -> {"file_id": ..., "title": ...}

MEDALS = ["🥇", "🥈", "🥉"]


def is_admin(user_id):
    return db.is_admin_db(user_id)


# ================= ASOSIY MENYU =================

DIVIDER = "━━━━━━━━━━━━━━━"


def main_menu(user_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        types.KeyboardButton("🍿 Kino qidirish"),
        types.KeyboardButton("🔥 TOP kinolar"),
    )
    kb.add(types.KeyboardButton("📈 Statistika"))
    kb.add(types.KeyboardButton("🆘 Yordam"))
    if is_admin(user_id):
        kb.add(types.KeyboardButton("⚙️ Admin panel"))
    return kb


def admin_panel_menu():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("➕ Yangi kino", callback_data="adm_add"),
        types.InlineKeyboardButton("🗑 O'chirish", callback_data="adm_del"),
    )
    kb.add(
        types.InlineKeyboardButton("📋 Kinolar ro'yxati", callback_data="adm_list"),
        types.InlineKeyboardButton("📈 To'liq statistika", callback_data="adm_stats"),
    )
    kb.add(
        types.InlineKeyboardButton("👑 Admin qo'shish", callback_data="adm_addadmin"),
        types.InlineKeyboardButton("🚫 Adminni olib tashlash", callback_data="adm_deladmin"),
    )
    kb.add(
        types.InlineKeyboardButton("📋 Adminlar ro'yxati", callback_data="adm_listadmins"),
    )
    return kb


def back_to_menu_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="back_main"))
    return kb


# ================= /start =================

@bot.message_handler(commands=["start"])
def cmd_start(message):
    db.add_user(message.from_user.id, message.from_user.username or "")
    user_state.pop(message.from_user.id, None)
    name = message.from_user.first_name or "do'stim"
    text = (
        f"🎥✨ <b>XUSH KELIBSIZ, {name}!</b> ✨🎥\n"
        f"{DIVIDER}\n"
        "Minglab kinolar bir necha soniyada siznikida! 🍿🎬\n\n"
        "🍿 <b>Kino qidirish</b> — kodni yuboring, video darhol keladi\n"
        "🔥 <b>TOP kinolar</b> — eng sevimli filmlar reytingi\n"
        "📈 <b>Statistika</b> — bot haqida raqamlar\n"
        "🆘 <b>Yordam</b> — savol yoki muammo bo'lsa, adminlarga yozing\n"
        f"{DIVIDER}\n"
        "👇 Boshlash uchun tugmani tanlang"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_menu(message.from_user.id))


# ================= ASOSIY TUGMALAR =================

@bot.message_handler(func=lambda m: m.text == "🍿 Kino qidirish")
def btn_search(message):
    user_state[message.from_user.id] = "waiting_code"
    bot.send_message(
        message.chat.id,
        "🔎✨ <b>Kino qidiruv rejimi yoqildi!</b>\n"
        f"{DIVIDER}\n"
        "🔢 Kino kodini yuboring, masalan: <b>101</b>\n"
        "🎬 Video bir zumda sizga keladi!",
        reply_markup=types.ReplyKeyboardRemove()
    )


@bot.message_handler(func=lambda m: m.text == "🔥 TOP kinolar")
def btn_top(message):
    movies = db.get_top_movies(10)
    if not movies:
        bot.send_message(message.chat.id, "😔 Hozircha kinolar mavjud emas.\nTez orada qiziqarli kinolar qo'shiladi! 🎬")
        return
    text = f"🔥✨ <b>ENG OMMABOP KINOLAR</b> ✨🔥\n{DIVIDER}\n\n"
    for i, m in enumerate(movies):
        prefix = MEDALS[i] if i < 3 else f"　{i + 1}."
        title = m["title"] or "Nomsiz"
        text += f"{prefix} <b>{title}</b>\n     🔑 <code>{m['code']}</code>   📥 {m['downloads']} marta\n\n"
    text += f"{DIVIDER}\n🎬 O'zingizga yoqqan kinoning kodini yuboring!"
    bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda m: m.text == "📈 Statistika")
def btn_stats(message):
    text = (
        f"📊✨ <b>BOT STATISTIKASI</b> ✨📊\n"
        f"{DIVIDER}\n"
        f"🎬 Jami kinolar:  <b>{db.movie_count()}</b>\n"
        f"👥 Foydalanuvchilar:  <b>{db.user_count()}</b>\n"
        f"📥 Yuklab olishlar:  <b>{db.total_downloads()}</b>\n"
        f"{DIVIDER}\n"
        "🚀 Bot har kuni o'sib bormoqda!"
    )
    bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda m: m.text == "🆘 Yordam")
def btn_help(message):
    user_state[message.from_user.id] = "waiting_help_message"
    bot.send_message(
        message.chat.id,
        f"🆘✨ <b>YORDAM XIZMATI</b> ✨🆘\n"
        f"{DIVIDER}\n"
        "✍️ Savolingiz yoki muammoingizni yozib yuboring.\n"
        "📨 Xabaringiz to'g'ridan-to'g'ri adminlarga yetkaziladi va "
        "imkon qadar tezroq javob berishadi.\n"
        f"{DIVIDER}\n"
        "💬 Endi xabaringizni yozing 👇",
        reply_markup=types.ReplyKeyboardRemove()
    )


@bot.message_handler(func=lambda m: m.text == "⚙️ Admin panel")
def btn_admin(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "⛔ Bu bo'lim faqat adminlar uchun mo'ljallangan.")
        return
    bot.send_message(
        message.chat.id,
        f"⚙️✨ <b>ADMIN PANEL</b> ✨⚙️\n{DIVIDER}\n🛠 Kerakli bo'limni tanlang:",
        reply_markup=admin_panel_menu()
    )


# ================= ADMIN INLINE TUGMALAR =================

@bot.callback_query_handler(func=lambda c: c.data == "back_main")
def cb_back(call):
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == "adm_add")
def cb_add(call):
    if not is_admin(call.from_user.id):
        return bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q", show_alert=True)
    user_state[call.from_user.id] = "waiting_video"
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        f"🎬✨ <b>Yangi kino qo'shish</b> ✨🎬\n{DIVIDER}\n"
        "📤 Kino videosini (yoki faylini) yuboring.\n"
        "✏️ Caption (izoh) qismiga kino nomini yozib qo'ying — chiroyliroq bo'ladi!"
    )


@bot.callback_query_handler(func=lambda c: c.data == "adm_del")
def cb_del(call):
    if not is_admin(call.from_user.id):
        return bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q", show_alert=True)
    user_state[call.from_user.id] = "waiting_delete_code"
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, f"🗑✨ <b>Kino o'chirish</b>\n{DIVIDER}\n🔢 O'chirmoqchi bo'lgan kino kodini yuboring:")


@bot.callback_query_handler(func=lambda c: c.data == "adm_list")
def cb_list(call):
    if not is_admin(call.from_user.id):
        return bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q", show_alert=True)
    bot.answer_callback_query(call.id)
    movies = db.get_all_movies()
    if not movies:
        bot.send_message(call.message.chat.id, "📭 Hali kino qo'shilmagan.")
        return
    text = f"📋✨ <b>BARCHA KINOLAR</b> ✨📋\n{DIVIDER}\n\n"
    for m in movies[:50]:
        title = m["title"] or "Nomsiz"
        text += f"🎬 <b>{title}</b>\n     🔑 <code>{m['code']}</code>   📥 {m['downloads']}\n\n"
    bot.send_message(call.message.chat.id, text)


@bot.callback_query_handler(func=lambda c: c.data == "adm_stats")
def cb_admstats(call):
    if not is_admin(call.from_user.id):
        return bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q", show_alert=True)
    bot.answer_callback_query(call.id)
    top = db.get_top_movies(3)
    text = (
        f"📈✨ <b>TO'LIQ STATISTIKA</b> ✨📈\n{DIVIDER}\n"
        f"🎬 Jami kinolar:  <b>{db.movie_count()}</b>\n"
        f"👥 Foydalanuvchilar:  <b>{db.user_count()}</b>\n"
        f"📥 Yuklab olishlar:  <b>{db.total_downloads()}</b>\n"
        f"{DIVIDER}\n"
        "🏆 <b>ENG TOP 3 KINO:</b>\n\n"
    )
    if top:
        for i, m in enumerate(top):
            text += f"{MEDALS[i]} <b>{m['title'] or 'Nomsiz'}</b> — {m['downloads']} marta\n"
    else:
        text += "Hozircha ma'lumot yo'q 📭\n"
    bot.send_message(call.message.chat.id, text)


@bot.callback_query_handler(func=lambda c: c.data == "adm_addadmin")
def cb_addadmin(call):
    if not is_admin(call.from_user.id):
        return bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q", show_alert=True)
    user_state[call.from_user.id] = "waiting_new_admin_id"
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        f"👑✨ <b>Yangi admin qo'shish</b>\n{DIVIDER}\n"
        "🔢 Yangi adminning Telegram ID raqamini yuboring.\n\n"
        "ℹ️ ID bilmasangiz, o'sha odam @userinfobot ga <code>/start</code> bossin — "
        "u yerda o'z ID raqamini ko'radi."
    )


@bot.callback_query_handler(func=lambda c: c.data == "adm_deladmin")
def cb_deladmin(call):
    if not is_admin(call.from_user.id):
        return bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q", show_alert=True)
    user_state[call.from_user.id] = "waiting_remove_admin_id"
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        f"🚫✨ <b>Adminni olib tashlash</b>\n{DIVIDER}\n"
        "🔢 Olib tashlamoqchi bo'lgan adminning ID raqamini yuboring:"
    )


@bot.callback_query_handler(func=lambda c: c.data == "adm_listadmins")
def cb_listadmins(call):
    if not is_admin(call.from_user.id):
        return bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q", show_alert=True)
    bot.answer_callback_query(call.id)
    admins = db.get_all_admins()
    text = f"👑✨ <b>ADMINLAR RO'YXATI</b> ✨👑\n{DIVIDER}\n\n"
    if admins:
        for a in admins:
            text += f"🆔 <code>{a}</code>\n"
    else:
        text += "Hozircha admin yo'q 📭\n"
    bot.send_message(call.message.chat.id, text)


# ================= XABARLARNI QAYTA ISHLASH (HOLATLARGA QARAB) =================

@bot.message_handler(content_types=["video", "document"])
def handle_video(message):
    state = user_state.get(message.from_user.id)
    if state != "waiting_video" or not is_admin(message.from_user.id):
        return
    file_id = message.video.file_id if message.video else message.document.file_id
    title = message.caption or "Nomsiz"
    pending_upload[message.from_user.id] = {"file_id": file_id, "title": title}
    user_state[message.from_user.id] = "waiting_movie_code"
    bot.send_message(
        message.chat.id,
        f"✅ <b>Video qabul qilindi!</b>\n🎬 {title}\n{DIVIDER}\n"
        "🔢 Endi shu kino uchun kod raqamini yuboring (masalan: 101):"
    )


@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_text(message):
    uid = message.from_user.id
    state = user_state.get(uid)
    text = message.text.strip()

    # Foydalanuvchi Yordam xabarini yozmoqda
    if state == "waiting_help_message":
        admins = db.get_all_admins()
        username = f"@{message.from_user.username}" if message.from_user.username else "yo'q"
        forward_text = (
            f"🆘✨ <b>YANGI YORDAM SO'ROVI</b> ✨🆘\n"
            f"{DIVIDER}\n"
            f"👤 Ism: <b>{message.from_user.first_name or 'Nomsiz'}</b>\n"
            f"🔗 Username: {username}\n"
            f"🆔 ID: <code>{uid}</code>\n"
            f"{DIVIDER}\n"
            f"💬 <b>Xabar:</b>\n{text}\n"
            f"{DIVIDER}\n"
            f"↩️ Javob berish uchun shu foydalanuvchiga to'g'ridan-to'g'ri yozing: <code>{uid}</code>"
        )
        sent_count = 0
        for admin_id in admins:
            try:
                bot.send_message(admin_id, forward_text)
                sent_count += 1
            except Exception:
                pass  # admin botni bloklagan yoki boshqa xatolik bo'lsa, davom etamiz

        user_state.pop(uid, None)
        if sent_count > 0:
            bot.send_message(
                message.chat.id,
                f"✅✨ <b>Xabaringiz yuborildi!</b>\n{DIVIDER}\n"
                "📨 Adminlar tez orada javob berishadi.\n"
                "🙏 Murojaat uchun rahmat!",
                reply_markup=main_menu(uid)
            )
        else:
            bot.send_message(
                message.chat.id,
                "⚠️ Xabaringizni yuborishda muammo yuz berdi. Birozdan so'ng qaytadan urinib ko'ring.",
                reply_markup=main_menu(uid)
            )
        return

    # Admin yangi admin ID sini kiritmoqda
    if state == "waiting_new_admin_id" and is_admin(uid):
        if not text.isdigit():
            bot.send_message(message.chat.id, "❌ Faqat raqam yuboring (Telegram ID).")
            return
        new_id = int(text)
        db.add_admin(new_id)
        user_state.pop(uid, None)
        bot.send_message(
            message.chat.id,
            f"✅✨ <code>{new_id}</code> endi admin!\n"
            "U botga /start bossa, admin panelni ko'radi.",
            reply_markup=main_menu(uid)
        )
        return

    # Admin biror adminni olib tashlamoqchi
    if state == "waiting_remove_admin_id" and is_admin(uid):
        if not text.isdigit():
            bot.send_message(message.chat.id, "❌ Faqat raqam yuboring.")
            return
        rem_id = int(text)
        if rem_id == uid:
            bot.send_message(message.chat.id, "❌ O'zingizni adminlikdan olib tashlay olmaysiz.")
            return
        removed = db.remove_admin(rem_id)
        user_state.pop(uid, None)
        if removed:
            bot.send_message(message.chat.id, f"🚫 <code>{rem_id}</code> adminlikdan olib tashlandi.",
                              reply_markup=main_menu(uid))
        else:
            bot.send_message(message.chat.id, f"❌ Bunday admin topilmadi.", reply_markup=main_menu(uid))
        return

    # Foydalanuvchi kino kodini kiritmoqda
    if state == "waiting_code":
        movie = db.get_movie(text)
        if movie:
            db.increment_downloads(text)
            bot.send_video(
                message.chat.id,
                movie["file_id"],
                caption=(
                    f"🎬 <b>{movie['title'] or 'Nomsiz'}</b>\n"
                    f"{DIVIDER}\n"
                    f"🔑 Kod: <code>{movie['code']}</code>\n"
                    f"🔥 Yuklab olingan: <b>{movie['downloads'] + 1}</b> marta\n"
                    f"{DIVIDER}\n"
                    "🍿 Tomosha qilishdan zavq oling!"
                ),
            )
            bot.send_message(message.chat.id, "✨ Yana kino kodini yuborishingiz mumkin,\n"
                                                "yoki menyudan boshqa bo'limni tanlang 👇",
                              reply_markup=main_menu(uid))
        else:
            bot.send_message(message.chat.id, f"❌ <b>Bunday kodli kino topilmadi.</b>\n🔁 Qaytadan urinib ko'ring:")
        return

    # Admin kino kodini belgilayapti (upload jarayoni)
    if state == "waiting_movie_code" and is_admin(uid):
        data = pending_upload.pop(uid, None)
        if not data:
            bot.send_message(message.chat.id, "⚠️ Xatolik. Qaytadan urinib ko'ring.")
            user_state.pop(uid, None)
            return
        db.add_movie(text, data["file_id"], data["title"])
        user_state.pop(uid, None)
        bot.send_message(
            message.chat.id,
            f"🎉✨ <b>Kino muvaffaqiyatli saqlandi!</b> ✨🎉\n{DIVIDER}\n"
            f"🎬 Nomi: <b>{data['title']}</b>\n🔑 Kod: <code>{text}</code>",
            reply_markup=main_menu(uid)
        )
        return

    # Admin kino o'chirmoqchi
    if state == "waiting_delete_code" and is_admin(uid):
        deleted = db.delete_movie(text)
        user_state.pop(uid, None)
        if deleted:
            bot.send_message(message.chat.id, f"🗑✅ <code>{text}</code> kodli kino o'chirildi.",
                              reply_markup=main_menu(uid))
        else:
            bot.send_message(message.chat.id, f"❌ <code>{text}</code> kodli kino topilmadi.",
                              reply_markup=main_menu(uid))
        return

    # Hech qanday holat yo'q bo'lsa — kod sifatida sinab ko'ramiz
    movie = db.get_movie(text)
    if movie:
        db.increment_downloads(text)
        bot.send_video(
            message.chat.id,
            movie["file_id"],
            caption=(
                f"🎬 <b>{movie['title'] or 'Nomsiz'}</b>\n"
                f"{DIVIDER}\n"
                f"🔑 Kod: <code>{movie['code']}</code>\n"
                f"🔥 Yuklab olingan: <b>{movie['downloads'] + 1}</b> marta\n"
                f"{DIVIDER}\n"
                "🍿 Tomosha qilishdan zavq oling!"
            ),
        )
    else:
        bot.send_message(
            message.chat.id,
            "🤔 Tushunmadim. Quyidagi tugmalardan foydalaning 👇",
            reply_markup=main_menu(uid)
        )


if __name__ == "__main__":
    print("🤖 Bot ishga tushdi...")
    bot.infinity_polling(skip_pending=True)# Foydalanuvchi holatini vaqtinchalik saqlash uchun (kod kutish, video kutish va h.k.)
user_state = {}          # user_id -> "waiting_code" | "waiting_video" | "waiting_movie_code" | "waiting_delete_code"
pending_upload = {}      # user_id -> {"file_id": ..., "title": ...}

MEDALS = ["🥇", "🥈", "🥉"]


def is_admin(user_id):
    return user_id in ADMIN_IDS


# ================= ASOSIY MENYU =================

DIVIDER = "━━━━━━━━━━━━━━━"


def main_menu(user_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        types.KeyboardButton("🍿 Kino qidirish"),
        types.KeyboardButton("🔥 TOP kinolar"),
    )
    kb.add(types.KeyboardButton("📈 Statistika"))
    if is_admin(user_id):
        kb.add(types.KeyboardButton("⚙️ Admin panel"))
    return kb


def admin_panel_menu():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("➕ Yangi kino", callback_data="adm_add"),
        types.InlineKeyboardButton("🗑 O'chirish", callback_data="adm_del"),
    )
    kb.add(
        types.InlineKeyboardButton("📋 Kinolar ro'yxati", callback_data="adm_list"),
        types.InlineKeyboardButton("📈 To'liq statistika", callback_data="adm_stats"),
    )
    return kb


def back_to_menu_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="back_main"))
    return kb


# ================= /start =================

@bot.message_handler(commands=["start"])
def cmd_start(message):
    db.add_user(message.from_user.id, message.from_user.username or "")
    user_state.pop(message.from_user.id, None)
    name = message.from_user.first_name or "do'stim"
    text = (
        f"🎥✨ <b>XUSH KELIBSIZ, {name}!</b> ✨🎥\n"
        f"{DIVIDER}\n"
        "Minglab kinolar bir necha soniyada siznikida! 🍿🎬\n\n"
        "🍿 <b>Kino qidirish</b> — kodni yuboring, video darhol keladi\n"
        "🔥 <b>TOP kinolar</b> — eng sevimli filmlar reytingi\n"
        "📈 <b>Statistika</b> — bot haqida raqamlar\n"
        f"{DIVIDER}\n"
        "👇 Boshlash uchun tugmani tanlang"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_menu(message.from_user.id))


# ================= ASOSIY TUGMALAR =================

@bot.message_handler(func=lambda m: m.text == "🍿 Kino qidirish")
def btn_search(message):
    user_state[message.from_user.id] = "waiting_code"
    bot.send_message(
        message.chat.id,
        "🔎✨ <b>Kino qidiruv rejimi yoqildi!</b>\n"
        f"{DIVIDER}\n"
        "🔢 Kino kodini yuboring, masalan: <b>101</b>\n"
        "🎬 Video bir zumda sizga keladi!",
        reply_markup=types.ReplyKeyboardRemove()
    )


@bot.message_handler(func=lambda m: m.text == "🔥 TOP kinolar")
def btn_top(message):
    movies = db.get_top_movies(10)
    if not movies:
        bot.send_message(message.chat.id, "😔 Hozircha kinolar mavjud emas.\nTez orada qiziqarli kinolar qo'shiladi! 🎬")
        return
    text = f"🔥✨ <b>ENG OMMABOP KINOLAR</b> ✨🔥\n{DIVIDER}\n\n"
    for i, m in enumerate(movies):
        prefix = MEDALS[i] if i < 3 else f"　{i + 1}."
        title = m["title"] or "Nomsiz"
        text += f"{prefix} <b>{title}</b>\n     🔑 <code>{m['code']}</code>   📥 {m['downloads']} marta\n\n"
    text += f"{DIVIDER}\n🎬 O'zingizga yoqqan kinoning kodini yuboring!"
    bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda m: m.text == "📈 Statistika")
def btn_stats(message):
    text = (
        f"📊✨ <b>BOT STATISTIKASI</b> ✨📊\n"
        f"{DIVIDER}\n"
        f"🎬 Jami kinolar:  <b>{db.movie_count()}</b>\n"
        f"👥 Foydalanuvchilar:  <b>{db.user_count()}</b>\n"
        f"📥 Yuklab olishlar:  <b>{db.total_downloads()}</b>\n"
        f"{DIVIDER}\n"
        "🚀 Bot har kuni o'sib bormoqda!"
    )
    bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda m: m.text == "⚙️ Admin panel")
def btn_admin(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "⛔ Bu bo'lim faqat adminlar uchun mo'ljallangan.")
        return
    bot.send_message(
        message.chat.id,
        f"⚙️✨ <b>ADMIN PANEL</b> ✨⚙️\n{DIVIDER}\n🛠 Kerakli bo'limni tanlang:",
        reply_markup=admin_panel_menu()
    )


# ================= ADMIN INLINE TUGMALAR =================

@bot.callback_query_handler(func=lambda c: c.data == "back_main")
def cb_back(call):
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == "adm_add")
def cb_add(call):
    if not is_admin(call.from_user.id):
        return bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q", show_alert=True)
    user_state[call.from_user.id] = "waiting_video"
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        f"🎬✨ <b>Yangi kino qo'shish</b> ✨🎬\n{DIVIDER}\n"
        "📤 Kino videosini (yoki faylini) yuboring.\n"
        "✏️ Caption (izoh) qismiga kino nomini yozib qo'ying — chiroyliroq bo'ladi!"
    )


@bot.callback_query_handler(func=lambda c: c.data == "adm_del")
def cb_del(call):
    if not is_admin(call.from_user.id):
        return bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q", show_alert=True)
    user_state[call.from_user.id] = "waiting_delete_code"
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, f"🗑✨ <b>Kino o'chirish</b>\n{DIVIDER}\n🔢 O'chirmoqchi bo'lgan kino kodini yuboring:")


@bot.callback_query_handler(func=lambda c: c.data == "adm_list")
def cb_list(call):
    if not is_admin(call.from_user.id):
        return bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q", show_alert=True)
    bot.answer_callback_query(call.id)
    movies = db.get_all_movies()
    if not movies:
        bot.send_message(call.message.chat.id, "📭 Hali kino qo'shilmagan.")
        return
    text = f"📋✨ <b>BARCHA KINOLAR</b> ✨📋\n{DIVIDER}\n\n"
    for m in movies[:50]:
        title = m["title"] or "Nomsiz"
        text += f"🎬 <b>{title}</b>\n     🔑 <code>{m['code']}</code>   📥 {m['downloads']}\n\n"
    bot.send_message(call.message.chat.id, text)


@bot.callback_query_handler(func=lambda c: c.data == "adm_stats")
def cb_admstats(call):
    if not is_admin(call.from_user.id):
        return bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q", show_alert=True)
    bot.answer_callback_query(call.id)
    top = db.get_top_movies(3)
    text = (
        f"📈✨ <b>TO'LIQ STATISTIKA</b> ✨📈\n{DIVIDER}\n"
        f"🎬 Jami kinolar:  <b>{db.movie_count()}</b>\n"
        f"👥 Foydalanuvchilar:  <b>{db.user_count()}</b>\n"
        f"📥 Yuklab olishlar:  <b>{db.total_downloads()}</b>\n"
        f"{DIVIDER}\n"
        "🏆 <b>ENG TOP 3 KINO:</b>\n\n"
    )
    if top:
        for i, m in enumerate(top):
            text += f"{MEDALS[i]} <b>{m['title'] or 'Nomsiz'}</b> — {m['downloads']} marta\n"
    else:
        text += "Hozircha ma'lumot yo'q 📭\n"
    bot.send_message(call.message.chat.id, text)


# ================= XABARLARNI QAYTA ISHLASH (HOLATLARGA QARAB) =================

@bot.message_handler(content_types=["video", "document"])
def handle_video(message):
    state = user_state.get(message.from_user.id)
    if state != "waiting_video" or not is_admin(message.from_user.id):
        return
    file_id = message.video.file_id if message.video else message.document.file_id
    title = message.caption or "Nomsiz"
    pending_upload[message.from_user.id] = {"file_id": file_id, "title": title}
    user_state[message.from_user.id] = "waiting_movie_code"
    bot.send_message(
        message.chat.id,
        f"✅ <b>Video qabul qilindi!</b>\n🎬 {title}\n{DIVIDER}\n"
        "🔢 Endi shu kino uchun kod raqamini yuboring (masalan: 101):"
    )


@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_text(message):
    uid = message.from_user.id
    state = user_state.get(uid)
    text = message.text.strip()

    # Foydalanuvchi kino kodini kiritmoqda
    if state == "waiting_code":
        movie = db.get_movie(text)
        if movie:
            db.increment_downloads(text)
            bot.send_video(
                message.chat.id,
                movie["file_id"],
                caption=(
                    f"🎬 <b>{movie['title'] or 'Nomsiz'}</b>\n"
                    f"{DIVIDER}\n"
                    f"🔑 Kod: <code>{movie['code']}</code>\n"
                    f"🔥 Yuklab olingan: <b>{movie['downloads'] + 1}</b> marta\n"
                    f"{DIVIDER}\n"
                    "🍿 Tomosha qilishdan zavq oling!"
                ),
            )
            bot.send_message(message.chat.id, "✨ Yana kino kodini yuborishingiz mumkin,\n"
                                                "yoki menyudan boshqa bo'limni tanlang 👇",
                              reply_markup=main_menu(uid))
        else:
            bot.send_message(message.chat.id, f"❌ <b>Bunday kodli kino topilmadi.</b>\n🔁 Qaytadan urinib ko'ring:")
        return

    # Admin kino kodini belgilayapti (upload jarayoni)
    if state == "waiting_movie_code" and is_admin(uid):
        data = pending_upload.pop(uid, None)
        if not data:
            bot.send_message(message.chat.id, "⚠️ Xatolik. Qaytadan urinib ko'ring.")
            user_state.pop(uid, None)
            return
        db.add_movie(text, data["file_id"], data["title"])
        user_state.pop(uid, None)
        bot.send_message(
            message.chat.id,
            f"🎉✨ <b>Kino muvaffaqiyatli saqlandi!</b> ✨🎉\n{DIVIDER}\n"
            f"🎬 Nomi: <b>{data['title']}</b>\n🔑 Kod: <code>{text}</code>",
            reply_markup=main_menu(uid)
        )
        return

    # Admin kino o'chirmoqchi
    if state == "waiting_delete_code" and is_admin(uid):
        deleted = db.delete_movie(text)
        user_state.pop(uid, None)
        if deleted:
            bot.send_message(message.chat.id, f"🗑✅ <code>{text}</code> kodli kino o'chirildi.",
                              reply_markup=main_menu(uid))
        else:
            bot.send_message(message.chat.id, f"❌ <code>{text}</code> kodli kino topilmadi.",
                              reply_markup=main_menu(uid))
        return

    # Hech qanday holat yo'q bo'lsa — kod sifatida sinab ko'ramiz
    movie = db.get_movie(text)
    if movie:
        db.increment_downloads(text)
        bot.send_video(
            message.chat.id,
            movie["file_id"],
            caption=(
                f"🎬 <b>{movie['title'] or 'Nomsiz'}</b>\n"
                f"{DIVIDER}\n"
                f"🔑 Kod: <code>{movie['code']}</code>\n"
                f"🔥 Yuklab olingan: <b>{movie['downloads'] + 1}</b> marta\n"
                f"{DIVIDER}\n"
                "🍿 Tomosha qilishdan zavq oling!"
            ),
        )
    else:
        bot.send_message(
            message.chat.id,
            "🤔 Tushunmadim. Quyidagi tugmalardan foydalaning 👇",
            reply_markup=main_menu(uid)
        )


if __name__ == "__main__":
    print("🤖 Bot ishga tushdi...")
    bot.infinity_polling(skip_pending=True)
