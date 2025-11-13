# bot.py - بات آموزشی فارسی
# GitHub: https://github.com/yourusername/educational-bot

import telebot
import json
import random
import os
import threading
import re
import time
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

print("🚀 بات آموزشی فارسی در حال راه‌اندازی...")

# ================== تنظیمات ==================
TOKEN = "8286761989:AAGYt9KYNga6CZVjaEK4sW0TS6hgHlrG4wA"  # جایگزین کنید با توکن واقعی
ADMIN_ID = [2144744835, 7123554622]  # آیدی ادمین‌ها

# مسیرهای ذخیره‌سازی
BASE_DIR = os.getcwd()
DATA_DIR = os.path.join(BASE_DIR, "data")
QUESTIONS_DIR = os.path.join(BASE_DIR, "questions")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(QUESTIONS_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users.json")
BANNED_FILE = os.path.join(DATA_DIR, "banned.json")
SESSION_FILE = os.path.join(DATA_DIR, "sessions.json")

# فایل‌های سوالات
QUESTIONS_FILES = {
    "7": os.path.join(QUESTIONS_DIR, "questions_7.json"),
    "8": os.path.join(QUESTIONS_DIR, "questions_8.json"), 
    "9": os.path.join(QUESTIONS_DIR, "questions_9.json"),
}

print("✅ مسیرهای ذخیره‌سازی تنظیم شد")

# ================== مدیریت داده‌ها ==================
class DataManager:
    @staticmethod
    def load_data(file_path, default={}):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default
    
    @staticmethod
    def save_data(data, file_path):
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ خطا در ذخیره‌سازی {file_path}: {e}")
            return False

# ================== مدیریت کاربران ==================
def load_users():
    return DataManager.load_data(USERS_FILE)

def save_users(users_data):
    return DataManager.save_data(users_data, USERS_FILE)

def load_banned():
    return DataManager.load_data(BANNED_FILE)

def save_banned(banned_data):
    return DataManager.save_data(banned_data, BANNED_FILE)

def is_admin(user_id):
    return user_id in ADMIN_ID

def user_exists(fullname):
    users = load_users()
    for user_data in users.values():
        if user_data.get("fullname") == fullname:
            return True
    return False

def get_user_by_name(fullname):
    users = load_users()
    for user_id, user_data in users.items():
        if user_data.get("fullname") == fullname:
            return int(user_id)
    return None

def add_user(telegram_id, fullname, username=None, grade=None):
    users = load_users()
    users[str(telegram_id)] = {
        "fullname": fullname,
        "username": username or "ندارد",
        "grade": grade,
        "score": 0,
        "join_date": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    return save_users(users)

def get_user(telegram_id):
    users = load_users()
    return users.get(str(telegram_id))

def update_grade(telegram_id, grade):
    users = load_users()
    if str(telegram_id) in users:
        users[str(telegram_id)]["grade"] = grade
        return save_users(users)
    return False

def update_score(telegram_id, points, operation="add"):
    users = load_users()
    if str(telegram_id) in users:
        if operation == "add":
            users[str(telegram_id)]["score"] = users[str(telegram_id)].get("score", 0) + points
        elif operation == "subtract":
            current = users[str(telegram_id)].get("score", 0)
            users[str(telegram_id)]["score"] = max(0, current - points)
        elif operation == "set":
            users[str(telegram_id)]["score"] = points
        return save_users(users)
    return False

def delete_user(fullname):
    users = load_users()
    for user_id, user_data in users.items():
        if user_data.get("fullname") == fullname:
            del users[user_id]
            return save_users(users)
    return False

def ban_user(fullname):
    banned = load_banned()
    user_id = get_user_by_name(fullname)
    if user_id:
        user = get_user(user_id)
        if user:
            banned[str(user_id)] = {
                "fullname": fullname,
                "username": user.get("username"),
                "banned_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "banned_by": "ADMIN"
            }
            return save_banned(banned)
    return False

def unban_user(fullname):
    banned = load_banned()
    user_id = get_user_by_name(fullname)
    if user_id and str(user_id) in banned:
        del banned[str(user_id)]
        return save_banned(banned)
    return False

def is_banned(telegram_id):
    banned = load_banned()
    return str(telegram_id) in banned

def get_top_users(limit=10):
    users = load_users()
    sorted_users = sorted(
        [(data["fullname"], data.get("score", 0)) for data in users.values()],
        key=lambda x: x[1],
        reverse=True
    )
    return sorted_users[:limit]

def get_all_users():
    users = load_users()
    user_list = []
    for user_id, user_data in users.items():
        user_list.append({
            "id": user_id,
            "fullname": user_data.get("fullname", "نامشخص"),
            "username": user_data.get("username", "ندارد"),
            "grade": user_data.get("grade", "تعیین نشده"),
            "score": user_data.get("score", 0),
            "join_date": user_data.get("join_date", "نامشخص")
        })
    return user_list

def get_banned_users():
    return load_banned()

# ================== مدیریت سوالات ==================
def load_questions(grade):
    file_path = QUESTIONS_FILES.get(str(grade))
    if not file_path or not os.path.exists(file_path):
        return []
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ خطا در بارگذاری سوالات پایه {grade}: {e}")
        return []

def get_questions_by_level(grade, level, count=10):
    questions = load_questions(grade)
    level_questions = [q for q in questions if q.get("level") == level]
    
    if len(level_questions) < count:
        return []
    
    return random.sample(level_questions, count)

# ================== منوها ==================
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("🎮 شروع بازی"),
        KeyboardButton("🏆 رنکینگ"), 
        KeyboardButton("👤 اکانت"),
        KeyboardButton("💎 درخواست مثبت"),
        KeyboardButton("🛠 تغییر پایه"),
        KeyboardButton("📞 پشتیبانی"),
        KeyboardButton("📚 راهنما")
    )
    return kb

def grade_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("7️⃣ هفتم"), KeyboardButton("8️⃣ هشتم"), KeyboardButton("9️⃣ نهم"))
    kb.row(KeyboardButton("🔙 بازگشت"))
    return kb

def level_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("🟢 آسان"), KeyboardButton("🟠 نرمال"), KeyboardButton("🔴 سخت"))
    kb.row(KeyboardButton("🔙 بازگشت"))
    return kb

def options_menu(options):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for option in options:
        kb.add(KeyboardButton(option))
    kb.row(KeyboardButton("🔙 بازگشت"))
    return kb

# ================== مدیریت جلسات بازی ==================
sessions = {}
sessions_lock = threading.Lock()
QUESTION_TIME = 20
QUESTIONS_PER_ROUND = 10
POINTS_MAP = {"easy": 2, "normal": 5, "hard": 10}
POSITIVE_THRESHOLD = 1000

def normalize_answer(text):
    if not text:
        return ""
    text = re.sub(r'[.,;:!?؟،]', '', text.strip())
    text = re.sub(r'\s+', ' ', text)
    return text.lower()

def compare_answers(user_answer, correct_answer):
    return normalize_answer(user_answer) == normalize_answer(correct_answer)

def start_quiz(telegram_id, grade, level):
    questions = get_questions_by_level(grade, level, QUESTIONS_PER_ROUND)
    if not questions:
        return False, "سوال کافی برای این سطح یافت نشد"
    
    session = {
        "questions": questions,
        "current_index": 0,
        "score": 0,
        "level": level,
        "timer": None
    }
    
    with sessions_lock:
        # حذف جلسه قبلی
        old_session = sessions.pop(telegram_id, None)
        if old_session and old_session.get("timer"):
            old_session["timer"].cancel()
        
        sessions[telegram_id] = session
    
    send_question(telegram_id)
    return True, "بازی شروع شد"

def send_question(telegram_id):
    with sessions_lock:
        session = sessions.get(telegram_id)
        if not session:
            return
        
        if session["current_index"] >= QUESTIONS_PER_ROUND:
            end_quiz(telegram_id)
            return
        
        question = session["questions"][session["current_index"]]
        question_num = session["current_index"] + 1
    
    # حذف تایمر قبلی
    if session.get("timer"):
        session["timer"].cancel()
    
    # ایجاد تایمر جدید
    timer = threading.Timer(QUESTION_TIME, handle_timeout, [telegram_id])
    timer.start()
    
    with sessions_lock:
        if telegram_id in sessions:
            sessions[telegram_id]["timer"] = timer
    
    # ارسال سوال
    question_text = f"🎯 سؤال {question_num}/{QUESTIONS_PER_ROUND}\n\n{question.get('question')}"
    options = question.get("options", [])
    
    if options:
        bot.send_message(telegram_id, question_text, reply_markup=options_menu(options))
    else:
        bot.send_message(telegram_id, question_text)

def handle_timeout(telegram_id):
    with sessions_lock:
        session = sessions.get(telegram_id)
        if not session:
            return
        
        session["current_index"] += 1
        if session.get("timer"):
            session["timer"] = None
    
    bot.send_message(telegram_id, "⏰ زمان تمام شد! به سوال بعدی می‌رویم...")
    send_question(telegram_id)

def process_answer(telegram_id, user_answer):
    with sessions_lock:
        session = sessions.get(telegram_id)
        if not session:
            return
        
        # متوقف کردن تایمر
        if session.get("timer"):
            session["timer"].cancel()
            session["timer"] = None
        
        current_index = session["current_index"]
        if current_index >= QUESTIONS_PER_ROUND:
            end_quiz(telegram_id)
            return
        
        question = session["questions"][current_index]
        correct_answer = question.get("answer", "").strip()
        
        if compare_answers(user_answer, correct_answer):
            points = POINTS_MAP.get(session["level"], 5)
            session["score"] += points
            bot.send_message(telegram_id, "✅ پاسخ درست! 🎉")
        else:
            bot.send_message(telegram_id, f"❌ پاسخ اشتباه!\nپاسخ صحیح: {correct_answer}")
        
        session["current_index"] += 1
    
    send_question(telegram_id)

def end_quiz(telegram_id):
    with sessions_lock:
        session = sessions.pop(telegram_id, None)
    
    if not session:
        return
    
    total_score = session["score"]
    level = session["level"]
    
    # محاسبه امتیاز نهایی
    final_score = total_score
    
    if level == "hard" and total_score < 50:
        final_score = 0
        message = "📉 نیاز به تلاش بیشتر! امتیاز شما زیر ۵۰ است."
    elif level == "normal" and total_score < 25:
        final_score = 0
        message = "📉 نیاز به تلاش بیشتر! امتیاز شما زیر ۲۵ است."
    elif level == "easy" and total_score < 10:
        final_score = 0
        message = "📉 نیاز به تلاش بیشتر! امتیاز شما زیر ۱۰ است."
    else:
        if total_score >= 90:
            message = f"🤩 عالی بودی! 🏅 امتیاز: {total_score}"
        elif total_score >= 70:
            message = f"😎 خیلی خوب! 🏅 امتیاز: {total_score}"
        elif total_score >= 50:
            message = f"😊 خوب بود! 🏅 امتیاز: {total_score}"
        else:
            message = f"😐 قابل قبول! 🏅 امتیاز: {total_score}"
    
    # ذخیره امتیاز
    if final_score > 0:
        update_score(telegram_id, final_score, "add")
        message += f"\n\n💰 {final_score} امتیاز به حساب شما اضافه شد!"
    else:
        message += f"\n\n💔 امتیازی دریافت نکردید!"
    
    bot.send_message(telegram_id, message, reply_markup=main_menu())

# ================== بات ==================
bot = telebot.TeleBot(TOKEN)

# ================== ثبت‌نام کاربران ==================
pending_registration = {}

@bot.message_handler(commands=['start'])
def start_command(message):
    telegram_id = message.from_user.id
    
    if is_banned(telegram_id):
        bot.send_message(telegram_id, "🚫 شما از این بات مسدود شده‌اید!")
        return
    
    user = get_user(telegram_id)
    if not user:
        bot.send_message(telegram_id, "👋 سلام! لطفاً نام و نام خانوادگی خود را وارد کنید:", 
                        reply_markup=telebot.types.ReplyKeyboardRemove())
        pending_registration[telegram_id] = {"step": "name"}
    else:
        bot.send_message(telegram_id, f"سلام {user['fullname']}! 😊", reply_markup=main_menu())

@bot.message_handler(func=lambda message: pending_registration.get(message.from_user.id, {}).get("step") == "name")
def process_name(message):
    telegram_id = message.from_user.id
    fullname = message.text.strip()
    
    if not fullname:
        bot.send_message(telegram_id, "❌ نام نمی‌تواند خالی باشد. دوباره وارد کنید:")
        return
    
    if user_exists(fullname):
        bot.send_message(telegram_id, "❌ این نام قبلاً ثبت شده است. نام دیگری انتخاب کنید:")
        return
    
    pending_registration[telegram_id] = {"step": "grade", "name": fullname}
    bot.send_message(telegram_id, "🎓 حالا پایه تحصیلی خود را انتخاب کنید:", reply_markup=grade_menu())

@bot.message_handler(func=lambda message: pending_registration.get(message.from_user.id, {}).get("step") == "grade")
def process_grade(message):
    telegram_id = message.from_user.id
    text = message.text.strip()
    
    if text == "🔙 بازگشت":
        del pending_registration[telegram_id]
        start_command(message)
        return
    
    grade_map = {"7️⃣ هفتم": "7", "8️⃣ هشتم": "8", "9️⃣ نهم": "9"}
    grade = grade_map.get(text)
    
    if not grade:
        bot.send_message(telegram_id, "❌ لطفاً یکی از گزینه‌ها را انتخاب کنید:", reply_markup=grade_menu())
        return
    
    user_data = pending_registration[telegram_id]
    fullname = user_data["name"]
    username = message.from_user.username or "ندارد"
    
    if add_user(telegram_id, fullname, username, grade):
        del pending_registration[telegram_id]
        bot.send_message(telegram_id, f"✅ ثبت‌نام کامل شد!\n👤 نام: {fullname}\n🎓 پایه: {grade}", 
                        reply_markup=main_menu())
    else:
        bot.send_message(telegram_id, "❌ خطا در ثبت‌نام! لطفاً دوباره تلاش کنید.")

# ================== دستورات ادمین ==================
@bot.message_handler(commands=['admin', 'help'])
def admin_help(message):
    telegram_id = message.from_user.id
    
    if not is_admin(telegram_id):
        bot.send_message(telegram_id, "❌ این دستور فقط برای ادمین‌ها قابل دسترسی است.")
        return
    
    help_text = """
🛠 **دستورات ادمین - پنل مدیریت**

👤 **مدیریت کاربران:**
`+ علی 100` - افزودن ۱۰۰ امتیاز به علی
`- علی 50` - کسر ۵۰ امتیاز از علی
`= علی 200` - تنظیم امتیاز علی روی ۲۰۰
`re علی` - حذف کاربر علی
`player` - لیست تمام کاربران

🔒 **مدیریت مسدودیت:**
`Ban علی` - مسدود کردن کاربر علی
`Unban علی` - آزاد کردن کاربر علی  
`banned` - لیست کاربران مسدود شده

📢 **ارسال پیام:**
`A متن پیام` - ارسال پیام به همه کاربران

📊 **اطلاعات:**
`/stats` - آمار کلی بات
`/admin` - نمایش این راهنما

💾 **مدیریت سیستم:**
`/backup` - ایجاد پشتیبان
`/sessions` - نمایش جلسات فعال
"""
    bot.send_message(telegram_id, help_text)

@bot.message_handler(commands=['stats'])
def show_stats(message):
    if not is_admin(message.from_user.id):
        return
    
    users = get_all_users()
    banned = get_banned_users()
    
    total_users = len(users)
    total_score = sum(user["score"] for user in users)
    active_sessions = len(sessions)
    
    stats_text = f"""
📊 **آمار کلی بات**

👥 کاربران کل: {total_users}
🚫 کاربران مسدود: {len(banned)}
🏆 مجموع امتیازات: {total_score}
🎮 جلسات فعال: {active_sessions}
🕒 آخرین بروزرسانی: {time.strftime("%Y-%m-%d %H:%M:%S")}
"""
    bot.send_message(message.chat.id, stats_text)

@bot.message_handler(commands=['sessions'])
def show_sessions(message):
    if not is_admin(message.from_user.id):
        return
    
    with sessions_lock:
        active_sessions = len(sessions)
        sessions_info = "\n".join([f"🆔 {user_id} - سوال {sess['current_index']+1}/{QUESTIONS_PER_ROUND}" 
                                 for user_id, sess in sessions.items()])
    
    sessions_text = f"""
🎮 **جلسات فعال: {active_sessions}**

{sessions_info if sessions_info else "❌ هیچ جلسه‌ای فعال نیست"}
"""
    bot.send_message(message.chat.id, sessions_text)

# ================== هندلر اصلی پیام‌ها ==================
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    telegram_id = message.from_user.id
    text = message.text.strip()
    
    # بررسی مسدودیت
    if is_banned(telegram_id):
        bot.send_message(telegram_id, "🚫 شما از این بات مسدود شده‌اید!")
        return
    
    # بررسی جلسه فعال
    with sessions_lock:
        if telegram_id in sessions:
            if text == "🔙 بازگشت":
                end_quiz(telegram_id)
                return
            process_answer(telegram_id, text)
            return
    
    # دستورات ادمین
    if is_admin(telegram_id):
        if text.startswith("+ "):
            # افزودن امتیاز: + علی 100
            try:
                parts = text[2:].strip().rsplit(" ", 1)
                if len(parts) == 2:
                    fullname, points = parts[0].strip(), int(parts[1])
                    user_id = get_user_by_name(fullname)
                    if user_id and update_score(user_id, points, "add"):
                        bot.send_message(telegram_id, f"✅ {points} امتیاز به {fullname} اضافه شد.")
                    else:
                        bot.send_message(telegram_id, "❌ کاربر یافت نشد.")
                else:
                    bot.send_message(telegram_id, "❌ فرمت اشتباه. مثال: + علی 100")
            except:
                bot.send_message(telegram_id, "❌ خطا در پردازش دستور.")
            return
        
        elif text.startswith("- "):
            # کسر امتیاز: - علی 50
            try:
                parts = text[2:].strip().rsplit(" ", 1)
                if len(parts) == 2:
                    fullname, points = parts[0].strip(), int(parts[1])
                    user_id = get_user_by_name(fullname)
                    if user_id and update_score(user_id, points, "subtract"):
                        bot.send_message(telegram_id, f"✅ {points} امتیاز از {fullname} کسر شد.")
                    else:
                        bot.send_message(telegram_id, "❌ کاربر یافت نشد.")
                else:
                    bot.send_message(telegram_id, "❌ فرمت اشتباه. مثال: - علی 50")
            except:
                bot.send_message(telegram_id, "❌ خطا در پردازش دستور.")
            return
        
        elif text.startswith("= "):
            # تنظیم امتیاز: = علی 200
            try:
                parts = text[2:].strip().rsplit(" ", 1)
                if len(parts) == 2:
                    fullname, points = parts[0].strip(), int(parts[1])
                    user_id = get_user_by_name(fullname)
                    if user_id and update_score(user_id, points, "set"):
                        bot.send_message(telegram_id, f"✅ امتیاز {fullname} روی {points} تنظیم شد.")
                    else:
                        bot.send_message(telegram_id, "❌ کاربر یافت نشد.")
                else:
                    bot.send_message(telegram_id, "❌ فرمت اشتباه. مثال: = علی 200")
            except:
                bot.send_message(telegram_id, "❌ خطا در پردازش دستور.")
            return
        
        elif text == "banned":
            # لیست مسدود شده‌ها
            banned_users = get_banned_users()
            if not banned_users:
                bot.send_message(telegram_id, "✅ هیچ کاربری مسدود نیست.")
                return
            
            banned_text = "🔒 لیست کاربران مسدود شده:\n\n"
            for user_id, user_data in banned_users.items():
                banned_text += f"👤 {user_data['fullname']}\n🆔 {user_id}\n⏰ {user_data['banned_at']}\n────────────\n"
            
            bot.send_message(telegram_id, banned_text)
            return
        
        elif text.startswith("A "):
            # ارسال پیام همگانی: A سلام به همه
            broadcast_message = text[2:].strip()
            if not broadcast_message:
                bot.send_message(telegram_id, "❌ پیام نمی‌تواند خالی باشد.")
                return
            
            users = get_all_users()
            banned = get_banned_users()
            sent_count = 0
            
            for user in users:
                if user["id"] not in banned:
                    try:
                        bot.send_message(user["id"], f"📢 پیام همگانی:\n\n{broadcast_message}")
                        sent_count += 1
                    except:
                        continue
            
            bot.send_message(telegram_id, f"✅ پیام به {sent_count} کاربر ارسال شد.")
            return
        
        elif text == "player":
            # لیست کاربران
            users = get_all_users()
            if not users:
                bot.send_message(telegram_id, "❌ هیچ کاربری ثبت‌نام نکرده است.")
                return
            
            users_text = "👥 لیست کاربران:\n\n"
            for i, user in enumerate(users[:20], 1):  # فقط ۲۰ کاربر اول
                users_text += f"{i}. {user['fullname']}\n🆔 {user['id']}\n📊 {user['score']} امتیاز\n🎓 {user['grade']}\n────────────\n"
            
            if len(users) > 20:
                users_text += f"\n📋 و {len(users) - 20} کاربر دیگر..."
            
            bot.send_message(telegram_id, users_text)
            return
    
    # منوی اصلی برای کاربران عادی
    user = get_user(telegram_id)
    if not user:
        start_command(message)
        return
    
    if text == "🎮 شروع بازی":
        if not user.get("grade"):
            bot.send_message(telegram_id, "❌ لطفاً ابتدا پایه تحصیلی خود را تنظیم کنید.", reply_markup=main_menu())
            return
        bot.send_message(telegram_id, "🎯 سطح دشواری را انتخاب کنید:", reply_markup=level_menu())
    
    elif text in ["🟢 آسان", "🟠 نرمال", "🔴 سخت"]:
        level_map = {"🟢 آسان": "easy", "🟠 نرمال": "normal", "🔴 سخت": "hard"}
        level = level_map[text]
        grade = user.get("grade")
        
        success, result = start_quiz(telegram_id, grade, level)
        if not success:
            bot.send_message(telegram_id, f"❌ {result}", reply_markup=main_menu())
    
    elif text == "🏆 رنکینگ":
        top_users = get_top_users(10)
        if not top_users:
            bot.send_message(telegram_id, "❌ هنوز کاربری امتیازی ندارد.", reply_markup=main_menu())
            return
        
        ranking_text = "🏆 رتبه‌بندی برترین کاربران:\n\n"
        for i, (name, score) in enumerate(top_users, 1):
            ranking_text += f"{i}. {name}: {score} امتیاز\n"
        
        bot.send_message(telegram_id, ranking_text, reply_markup=main_menu())
    
    elif text == "👤 اکانت":
        user_info = f"""
👤 اطلاعات حساب شما:

📛 نام: {user['fullname']}
🎓 پایه: {user.get('grade', 'تعیین نشده')}
🏆 امتیاز: {user.get('score', 0)}
📅 تاریخ عضویت: {user.get('join_date', 'نامشخص')}
"""
        bot.send_message(telegram_id, user_info, reply_markup=main_menu())
    
    elif text == "💎 درخواست مثبت":
        score = user.get("score", 0)
        if score >= POSITIVE_THRESHOLD:
            if update_score(telegram_id, POSITIVE_THRESHOLD, "subtract"):
                bot.send_message(telegram_id, 
                               f"✅ درخواست مثبت شما ثبت شد!\n💰 {POSITIVE_THRESHOLD} امتیاز از حساب شما کسر شد.")
                # اطلاع به ادمین
                for admin_id in ADMIN_ID:
                    try:
                        bot.send_message(admin_id, 
                                       f"📩 درخواست مثبت جدید:\n👤 کاربر: {user['fullname']}\n🆔 آیدی: {telegram_id}")
                    except:
                        pass
            else:
                bot.send_message(telegram_id, "❌ خطا در پردازش درخواست!")
        else:
            bot.send_message(telegram_id, 
                           f"❌ امتیاز کافی ندارید!\n💎 نیاز: {POSITIVE_THRESHOLD} امتیاز\n💰 فعلی: {score} امتیاز")
    
    elif text == "🛠 تغییر پایه":
        bot.send_message(telegram_id, "🎓 پایه جدید را انتخاب کنید:", reply_markup=grade_menu())
        bot.register_next_step_handler(message, change_grade)

    elif text == "📞 پشتیبانی":
        support_text = """
🤝 **پشتیبانی بات آموزشی**

📞 **آیدی پشتیبانی:**
@Mahyar015

✨ **خدمات پشتیبانی:**
• پاسخ به سوالات فنی
• راهنمایی در استفاده از بات  
• گزارش مشکلات و باگ‌ها
• پیشنهادات و انتقادات

🕒 **پاسخگویی:**
۲۴ ساعته، ۷ روز هفته

🚀 **ما اینجاییم تا کمک کنیم!**
"""
        bot.send_message(telegram_id, support_text, reply_markup=main_menu())

    elif text == "📚 راهنما":
        help_text = """
📚 **راهنمای کامل بات آموزشی**

🎮 **شروع بازی:**
۱. انتخاب پایه تحصیلی (هفتم، هشتم، نهم)
۲. انتخاب سطح دشواری (آسان، نرمال، سخت)
۳. پاسخ به ۱۰ سوال در زمان محدود

🏆 **سیستم امتیازدهی:**
• 🟢 آسان: ۲ امتیاز برای هر پاسخ صحیح
• 🟠 نرمال: ۵ امتیاز برای هر پاسخ صحیح  
• 🔴 سخت: ۱۰ امتیاز برای هر پاسخ صحیح

💎 **درخواست مثبت:**
• نیاز به ۱۰۰۰ امتیاز
• برای دریافت کمک از ادمین

📊 **منوهای اصلی:**
• 🎮 شروع بازی - شروع چالش جدید
• 🏆 رنکینگ - مشاهده برترین‌ها
• 👤 اکانت - اطلاعات حساب کاربری
• 💎 درخواست مثبت - ارتباط با ادمین
• 🛠 تغییر پایه - تغییر پایه تحصیلی
• 📞 پشتیبانی - راهنمایی و کمک
• 📚 راهنما - همین صفحه!

⏰ **نکات مهم:**
• هر سوال ۲۰ ثانیه زمان دارد
• در صورت اتمام زمان، به سوال بعد می‌روید
• امتیاز بر اساس سطح بازی محاسبه می‌شود
"""
        bot.send_message(telegram_id, help_text, reply_markup=main_menu())

    elif text == "🔙 بازگشت":
        bot.send_message(telegram_id, "منوی اصلی:", reply_markup=main_menu())

    else:
        bot.send_message(telegram_id, "❌ لطفاً از گزینه‌های منو استفاده کنید.", reply_markup=main_menu())

def change_grade(message):
    telegram_id = message.from_user.id
    text = message.text.strip()
    
    if text == "🔙 بازگشت":
        bot.send_message(telegram_id, "منوی اصلی:", reply_markup=main_menu())
        return
    
    grade_map = {"7️⃣ هفتم": "7", "8️⃣ هشتم": "8", "9️⃣ نهم": "9"}
    grade = grade_map.get(text)
    
    if not grade:
        bot.send_message(telegram_id, "❌ لطفاً یکی از گزینه‌ها را انتخاب کنید:", reply_markup=grade_menu())
        bot.register_next_step_handler(message, change_grade)
        return
    
    if update_grade(telegram_id, grade):
        bot.send_message(telegram_id, f"✅ پایه شما به {grade} تغییر یافت.", reply_markup=main_menu())
    else:
        bot.send_message(telegram_id, "❌ خطا در تغییر پایه!", reply_markup=main_menu())

# ================== اجرای بات ==================
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 بات آموزشی فارسی - نسخه کامل")
    print("="*50)
    
    # بررسی فایل‌های ضروری
    print("\n📁 بررسی فایل‌ها:")
    print(f"✅ فایل کاربران: {os.path.exists(USERS_FILE)}")
    print(f"✅ فایل مسدودیت: {os.path.exists(BANNED_FILE)}")
    
    for grade, path in QUESTIONS_FILES.items():
        exists = os.path.exists(path)
        print(f"📚 سوالات پایه {grade}: {'✅ موجود' if exists else '❌ یافت نشد'}")
    
    print(f"\n🛡️ ادمین‌ها: {len(ADMIN_ID)} کاربر")
    print(f"🎮 سوالات در هر بازی: {QUESTIONS_PER_ROUND}")
    print(f"⏰ زمان هر سوال: {QUESTION_TIME} ثانیه")
    print(f"💎 آستانه درخواست مثبت: {POSITIVE_THRESHOLD} امتیاز")
    
    print("\n✅ همه چیز آماده است!")
    print("📱 بات در حال گوش دادن به پیام‌ها...")
    print("="*50)
    
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"❌ خطا در اجرای بات: {e}")
    finally:
        print("\n🛑 بات متوقف شد")