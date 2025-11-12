import telebot
import json
import random
import os
import threading
import re
import time
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

print("🚀 بات آموزشی فارسی - نسخه Railway")

# ================== تنظیمات بات ==================
TOKEN = "8286761989:AAGYt9KYNga6CZVjaEK4sW0TS6hgHlrG4wA"
ADMIN_ID = [2144744835, 7123554622]
CHANNEL_USERNAME = "@Login_Bot1"

# تنظیمات آنتی-اسپم
SPAM_LIMIT = 10  # حداکثر پیام در بازه زمانی
SPAM_TIME_WINDOW = 10  # بازه زمانی به ثانیه
SPAM_BAN_DURATION = 3600  # مدت بن به ثانیه (1 ساعت)

# مسیرهای ذخیره‌سازی
BASE_DIR = os.getcwd()
DATA_DIR = os.path.join(BASE_DIR, "bot_data")
QUESTIONS_DIR = BASE_DIR  # فایل‌ها در مسیر اصلی هستند

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(QUESTIONS_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users_data.json")
BANNED_USERS_FILE = os.path.join(DATA_DIR, "banned_users.json")
SPAM_TRACKER_FILE = os.path.join(DATA_DIR, "spam_tracker.json")

QUESTIONS_FILES = {
    "7": os.path.join(QUESTIONS_DIR, "Questions7.json"),
    "8": os.path.join(QUESTIONS_DIR, "Questions8.json"),
    "9": os.path.join(QUESTIONS_DIR, "Questions9.json"),
}

print("✅ مسیرهای ذخیره‌سازی تنظیم شد")

# ================== مدیریت داده‌ها ==================
class DataManager:
    def __init__(self):
        self.data_dir = DATA_DIR
        self.users_file = USERS_FILE
        self.banned_file = BANNED_USERS_FILE
        self.spam_file = SPAM_TRACKER_FILE
        os.makedirs(self.data_dir, exist_ok=True)
        
    def load_data(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    
    def save_data(self, data, file_path):
        try:
            temp_file = file_path + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, file_path)
            return True
        except Exception as e:
            print(f"❌ خطا در ذخیره‌سازی: {e}")
            return False

data_manager = DataManager()

# ================== مدیریت اسپم ==================
def load_spam_tracker():
    return data_manager.load_data(SPAM_TRACKER_FILE)

def save_spam_tracker(spam_data):
    return data_manager.save_data(spam_data, SPAM_TRACKER_FILE)

def check_spam(telegram_id):
    """بررسی اسپم بودن کاربر"""
    spam_tracker = load_spam_tracker()
    user_data = spam_tracker.get(str(telegram_id), {})
    messages = user_data.get("messages", [])
    
    # حذف پیام‌های قدیمی
    current_time = time.time()
    recent_messages = [msg_time for msg_time in messages if current_time - msg_time <= SPAM_TIME_WINDOW]
    
    # اضافه کردن پیام جدید
    recent_messages.append(current_time)
    
    # ذخیره‌سازی
    spam_tracker[str(telegram_id)] = {
        "messages": recent_messages,
        "last_check": current_time
    }
    save_spam_tracker(spam_tracker)
    
    # بررسی تعداد پیام‌ها
    if len(recent_messages) >= SPAM_LIMIT:
        return True
    return False

def auto_ban_user(telegram_id, reason="اسپم"):
    """بن خودکار کاربر"""
    banned_users = load_banned_users()
    user = get_user(telegram_id)
    
    if user:
        fullname = user[1]
        username = user[2] if user[2] else "ندارد"
        
        banned_users[str(telegram_id)] = {
            "fullname": fullname,
            "username": username,
            "banned_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "banned_by": "SYSTEM",
            "reason": reason,
            "banned_until": time.time() + SPAM_BAN_DURATION
        }
        save_banned_users(banned_users)
        
        # ارسال پیام به ادمین
        for admin_id in ADMIN_ID:
            try:
                bot.send_message(
                    admin_id,
                    f"🚫 کاربر به دلیل اسپم بن شد:\n"
                    f"👤 نام: {fullname}\n"
                    f"📱 یوزرنیم: @{username}\n"
                    f"🆔 آیدی: {telegram_id}\n"
                    f"⏰ زمان بن: {SPAM_BAN_DURATION//3600} ساعت\n"
                    f"📝 دلیل: {reason}"
                )
            except:
                pass
        
        return True
    return False

def is_temp_banned(telegram_id):
    """بررسی بن موقت"""
    banned_users = load_banned_users()
    user_data = banned_users.get(str(telegram_id))
    
    if user_data and user_data.get("banned_by") == "SYSTEM":
        banned_until = user_data.get("banned_until", 0)
        if time.time() < banned_until:
            return True
        else:
            # حذف بن اگر زمانش گذشته
            del banned_users[str(telegram_id)]
            save_banned_users(banned_users)
            return False
    return False

# ================== مدیریت کاربران ==================
def load_users():
    return data_manager.load_data(USERS_FILE)

def save_users(users_data):
    return data_manager.save_data(users_data, USERS_FILE)

def load_banned_users():
    return data_manager.load_data(BANNED_USERS_FILE)

def save_banned_users(banned_data):
    return data_manager.save_data(banned_data, BANNED_USERS_FILE)

def fullname_exists(fullname):
    users = load_users()
    for user_id, user_data in users.items():
        if user_data.get("fullname") == fullname:
            return int(user_id)
    return None

def add_user(telegram_id, fullname, username=None, grade=None):
    users = load_users()
    users[str(telegram_id)] = {
        "fullname": fullname,
        "username": username,
        "grade": grade,
        "score": 0,
        "join_date": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    save_users(users)

def get_user(telegram_id):
    users = load_users()
    user_data = users.get(str(telegram_id))
    if user_data:
        return (
            telegram_id,
            user_data.get("fullname"),
            user_data.get("username"),
            user_data.get("grade"),
            user_data.get("score", 0)
        )
    return None

def update_grade(telegram_id, grade):
    users = load_users()
    if str(telegram_id) in users:
        users[str(telegram_id)]["grade"] = grade
        save_users(users)

def get_score(telegram_id):
    user = get_user(telegram_id)
    return user[4] if user else 0

def add_score(telegram_id, points):
    users = load_users()
    if str(telegram_id) in users:
        users[str(telegram_id)]["score"] = users[str(telegram_id)].get("score", 0) + points
        save_users(users)

def subtract_score(telegram_id, points):
    users = load_users()
    if str(telegram_id) in users:
        current_score = users[str(telegram_id)].get("score", 0)
        users[str(telegram_id)]["score"] = max(0, current_score - points)
        save_users(users)

def set_score(telegram_id, points):
    users = load_users()
    if str(telegram_id) in users:
        users[str(telegram_id)]["score"] = points
        save_users(users)

def delete_user_by_fullname(fullname):
    users = load_users()
    for user_id, user_data in users.items():
        if user_data.get("fullname") == fullname:
            del users[user_id]
            save_users(users)
            return True
    return False

def ban_user(fullname):
    """بن کردن کاربر توسط ادمین"""
    banned_users = load_banned_users()
    user_id = fullname_exists(fullname)
    if user_id:
        user = get_user(user_id)
        if user:
            banned_users[str(user_id)] = {
                "fullname": fullname,
                "username": user[2],
                "banned_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "banned_by": "ADMIN",
                "reason": "دستوری"
            }
            save_banned_users(banned_users)
            return True
    return False

def unban_user(fullname):
    """آنبن کردن کاربر"""
    banned_users = load_banned_users()
    user_id = fullname_exists(fullname)
    if user_id and str(user_id) in banned_users:
        del banned_users[str(user_id)]
        save_banned_users(banned_users)
        return True
    return False

def is_banned(telegram_id):
    """بررسی بن بودن کاربر"""
    if is_temp_banned(telegram_id):
        return True
        
    banned_users = load_banned_users()
    return str(telegram_id) in banned_users

def top_users(limit=10):
    users = load_users()
    sorted_users = sorted(
        [(data["fullname"], data.get("score", 0)) for data in users.values()],
        key=lambda x: x[1],
        reverse=True
    )
    return sorted_users[:limit]

def all_user_ids():
    users = load_users()
    return [int(user_id) for user_id in users.keys()]

def get_all_users():
    """دریافت لیست کامل تمام کاربران"""
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
    """دریافت لیست کاربران بن شده"""
    return load_banned_users()

# ================== منوها ==================
def main_menu_markup():
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

def grade_markup(show_back_button=True):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row(KeyboardButton("7️⃣ هفتم"), KeyboardButton("8️⃣ هشتم"), KeyboardButton("9️⃣ نهم"))
    if show_back_button:
        kb.row(KeyboardButton("🔙 بازگشت به منوی اصلی"))
    return kb

def level_markup():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row(KeyboardButton("🟢 آسان 😌"), KeyboardButton("🟠 نرمال 😎"), KeyboardButton("🔴 سخت 😈"))
    kb.row(KeyboardButton("🔙 بازگشت به منوی اصلی"))
    return kb

def options_markup(options):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for o in options:
        kb.add(KeyboardButton(o))
    kb.row(KeyboardButton("🔙 بازگشت به منوی اصلی"))
    return kb

# ================== جلسات ==================
sessions = {}
sessions_lock = threading.Lock()
QUESTION_TIME = 20
QUESTIONS_PER_ROUND = 10
POINTS_MAP = {"easy": 2, "normal": 5, "hard": 10}
POSITIVE_THRESHOLD = 1000

def normalize_answer(text):
    """نرمالایز کردن پاسخ برای مقایسه بهتر"""
    if not text:
        return ""
    
    text = re.sub(r'[.,;:!?؟،:：]', '', text.strip())
    text = re.sub(r'\s+', ' ', text)
    text = text.lower()
    
    return text

def debug_answer_comparison(user_answer, correct_answer):
    """دیباگ مقایسه پاسخ‌ها"""
    normalized_user = normalize_answer(user_answer)
    normalized_correct = normalize_answer(correct_answer)
    
    return normalized_user == normalized_correct

def start_quiz_for_user(telegram_id, grade, level_key):
    # بارگذاری سوالات از فایل JSON در پوشه Questions
    questions_file = QUESTIONS_FILES.get(grade)
    if not questions_file or not os.path.exists(questions_file):
        bot.send_message(telegram_id, f"❌ فایل سوالات برای پایه {grade} یافت نشد!\n\n📁 مسیر: {questions_file}", reply_markup=main_menu_markup())
        return False, "فایل سوالات موجود نیست"
    
    try:
        with open(questions_file, "r", encoding="utf-8") as f:
            all_questions = json.load(f)
        
        # فیلتر سوالات بر اساس سطح
        level_questions = [q for q in all_questions if q.get("level") == level_key]
        
        if len(level_questions) < QUESTIONS_PER_ROUND:
            bot.send_message(telegram_id, f"❌ سوالات کافی برای سطح {level_key} یافت نشد! (نیاز: {QUESTIONS_PER_ROUND}، موجود: {len(level_questions)})", reply_markup=main_menu_markup())
            return False, "سوالات کافی نیست"
        
        # انتخاب تصادفی سوالات
        questions = random.sample(level_questions, QUESTIONS_PER_ROUND)
        
    except Exception as e:
        print(f"خطا در بارگذاری سوالات: {e}")
        bot.send_message(telegram_id, f"❌ خطا در بارگذاری سوالات پایه {grade}!\n\n📁 مسیر: {questions_file}", reply_markup=main_menu_markup())
        return False, "خطا در بارگذاری"
    
    session = {
        "questions": questions,
        "index": 0,
        "correct_flags": [False] * QUESTIONS_PER_ROUND,
        "total_points": 0,
        "timer": None,
        "grade": grade,
        "level": level_key
    }

    with sessions_lock:
        prev = sessions.get(telegram_id)
        if prev and prev.get("timer"):
            prev["timer"].cancel()
        sessions[telegram_id] = session

    send_current_question(telegram_id)
    return True, "جلسه شروع شد."

def send_current_question(telegram_id):
    with sessions_lock:
        session = sessions.get(telegram_id)
        if not session:
            return
        idx = session["index"]
        if idx >= QUESTIONS_PER_ROUND:
            finish_quiz(telegram_id)
            return
        q = session["questions"][idx]
    
    question_text = f"🎯 سؤال {idx+1}/{QUESTIONS_PER_ROUND}\n\n{q.get('question')}"
    opts = q.get("options") or []

    try:
        if opts:
            options_text = "\n".join([f"• {opt}" for opt in opts])
            full_message = f"{question_text}\n\n📝 گزینه‌ها:\n{options_text}"
            bot.send_message(telegram_id, full_message, reply_markup=options_markup(opts))
        else:
            bot.send_message(telegram_id, question_text)
    except Exception as e:
        print(f"خطا در ارسال سوال: {e}")

def process_answer_in_session(message):
    telegram_id = message.from_user.id
    text = (message.text or "").strip()
    
    # چک کردن بازگشت
    if text == "🔙 بازگشت به منوی اصلی":
        with sessions_lock:
            session = sessions.pop(telegram_id, None)
            if session and session.get("timer"):
                session["timer"].cancel()
        bot.send_message(telegram_id, "بازگشت به منوی اصلی", reply_markup=main_menu_markup())
        return
    
    with sessions_lock:
        session = sessions.get(telegram_id)
        if not session:
            return
        
        idx = session["index"]
        if idx >= QUESTIONS_PER_ROUND:
            finish_quiz(telegram_id)
            return
        
        q = session["questions"][idx]
        correct_answer = q.get("answer", "").strip()
        user_answer = text
        
        is_correct = debug_answer_comparison(user_answer, correct_answer)
        
        if is_correct:
            lvl = q.get("level", "normal")
            pts = POINTS_MAP.get(lvl, 5)
            session["correct_flags"][idx] = True
            session["total_points"] += pts
            try:
                bot.send_message(telegram_id, "✅ پاسخ درست! 🎉")
            except:
                pass
        else:
            session["correct_flags"][idx] = False
            try:
                bot.send_message(telegram_id, f"❌ پاسخ اشتباه!\n\n📋 پاسخ صحیح: {correct_answer}")
            except:
                pass
            
        session["index"] += 1
    
    send_current_question(telegram_id)

def finish_quiz(telegram_id):
    with sessions_lock:
        session = sessions.pop(telegram_id, None)

    if not session:
        return

    total = session["total_points"]
    level = session["level"]
    
    final_score = 0
    message = ""
    
    if level == "hard":
        if total < 50:
            message = "📉 بیشتر تلاش کن پسر 🤢\nامتیاز شما زیر ۵۰ است و امتیازی دریافت نکردی!"
            final_score = 0
        elif 50 <= total <= 60:
            message = f"🥴 بدک نبود!\n🏅 امتیاز: {total}"
            final_score = total
        elif 61 <= total <= 70:
            message = f"😒 بدک نیس!\n🏅 امتیاز: {total}"
            final_score = total
        elif 71 <= total <= 80:
            message = f"😝 خوب بود!\n🏅 امتیاز: {total}"
            final_score = total
        elif 81 <= total <= 90:
            message = f"😎 خیلی خوب بود!\n🏅 امتیاز: {total}"
            final_score = total
        elif 91 <= total <= 100:
            message = f"🤩 عالی بودی!\n🏅 امتیاز: {total}"
            final_score = total
            
    elif level == "normal":
        if total < 25:
            message = "📉 امتیاز شما زیر ۲۵ است و امتیازی دریافت نکردی!"
            final_score = 0
        elif 25 <= total <= 30:
            message = f"🥴 بدک نبود!\n🏅 امتیاز: {total}"
            final_score = total
        elif 31 <= total <= 35:
            message = f"😒 بدک نیس!\n🏅 امتیاز: {total}"
            final_score = total
        elif 36 <= total <= 40:
            message = f"😝 خوب بود!\n🏅 امتیاز: {total}"
            final_score = total
        elif 41 <= total <= 45:
            message = f"😎 خیلی خوب بود!\n🏅 امتیاز: {total}"
            final_score = total
        elif 46 <= total <= 50:
            message = f"🤩 عالی بودی!\n🏅 امتیاز: {total}"
            final_score = total
            
    elif level == "easy":
        if total < 10:
            message = "📉 امتیاز شما زیر ۱۰ است و امتیازی دریافت نکردی!"
            final_score = 0
        elif 10 <= total <= 12:
            message = f"🥴 بدک نبود!\n🏅 امتیاز: {total}"
            final_score = total
        elif 13 <= total <= 14:
            message = f"😒 بدک نیس!\n🏅 امتیاز: {total}"
            final_score = total
        elif 15 <= total <= 16:
            message = f"😝 خوب بود!\n🏅 امتیاز: {total}"
            final_score = total
        elif 17 <= total <= 18:
            message = f"😎 خیلی خوب بود!\n🏅 امتیاز: {total}"
            final_score = total
        elif 19 <= total <= 20:
            message = f"🤩 عالی بودی!\n🏅 امتیاز: {total}"
            final_score = total

    if final_score > 0:
        add_score(telegram_id, final_score)
        message += f"\n\n💰 {final_score} امتیاز به حساب شما اضافه شد!"
    else:
        message += f"\n\n💔 امتیازی دریافت نکردی!"

    try:
        bot.send_message(telegram_id, message, reply_markup=main_menu_markup())
    except Exception as e:
        print(f"خطا در ارسال پیام پایانی: {e}")

# ================== ثبت‌نام ==================
pending_fullname = {}
pending_grade = {}
changing_grade = {}

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def cmd_start(message):
    if is_banned(message.from_user.id):
        remaining_time = get_remaining_ban_time(message.from_user.id)
        if remaining_time > 0:
            bot.send_message(message.chat.id, f"🚫 شما به دلیل اسپم بن شده‌اید!\n⏰ زمان باقی‌مانده: {remaining_time//60} دقیقه")
        else:
            bot.send_message(message.chat.id, "🚫 شما از بات مسدود شده‌اید!")
        return
        
    print(f"🚀 دستور start از کاربر: {message.from_user.id}")
    tid = message.from_user.id
    
    if not os.path.exists(USERS_FILE):
        save_users({})
    
    user = get_user(tid)
    if not user:
        bot.send_message(tid, "سلام! لطفاً **اسم و فامیل** خود را وارد کنید:", reply_markup=telebot.types.ReplyKeyboardRemove())
        pending_fullname[tid] = True
        bot.register_next_step_handler(message, receive_fullname)
    else:
        bot.send_message(tid, f"سلام {user[1]}! خوش آمدی.", reply_markup=main_menu_markup())

def get_remaining_ban_time(telegram_id):
    """دریافت زمان باقی‌مانده از بن"""
    banned_users = load_banned_users()
    user_data = banned_users.get(str(telegram_id))
    if user_data and user_data.get("banned_by") == "SYSTEM":
        banned_until = user_data.get("banned_until", 0)
        remaining = banned_until - time.time()
        return max(0, remaining)
    return 0

@bot.message_handler(commands=['help'])
def cmd_help(message):
    tid = message.from_user.id
    
    if tid not in ADMIN_ID:
        bot.send_message(tid, "❌ این دستور فقط برای ادمین‌ها قابل دسترسی است.")
        return
    
    help_text = """
🛠 **دستورات ادمین:**

👤 **مدیریت کاربران:**
`+ نام کاربر مقدار` - افزودن امتیاز
`- نام کاربر مقدار` - کاهش امتیاز  
`re نام کاربر` - حذف کاربر
`player` - لیست کاربران

🔒 **مدیریت بن:**
`Ban نام کاربر` - بن کردن کاربر
`Unban نام کاربر` - آنبن کردن کاربر
`banned` - لیست کاربران بن شده

📢 **ارسال پیام:**
`A متن پیام` - ارسال پیام همگانی

🆘 **راهنما:**
`/help` - نمایش این راهنما
    """
    bot.send_message(tid, help_text)

def receive_fullname(message):
    tid = message.from_user.id
    if not pending_fullname.get(tid):
        return
    name = (message.text or "").strip()
    if not name:
        bot.send_message(tid, "نام نمی‌تواند خالی باشد. دوباره وارد کنید:")
        bot.register_next_step_handler(message, receive_fullname)
        return
        
    if fullname_exists(name):
        bot.send_message(tid, "این نام قبلاً ثبت شده است. لطفاً نام دیگری وارد کنید:")
        bot.register_next_step_handler(message, receive_fullname)
        return
        
    username = message.from_user.username or ""
    add_user(tid, name, username)
    pending_fullname.pop(tid, None)
    pending_grade[tid] = True
    
    try:
        channel_message = f"👤 کاربر جدید ثبت‌نام کرد:\n🆔 آیدی: {tid}\n👤 نام: {name}\n📱 یوزرنیم: @{username if username else 'ندارد'}"
        bot.send_message(CHANNEL_USERNAME, channel_message)
    except Exception as e:
        print(f"خطا در ارسال به کانال: {e}")
    
    bot.send_message(tid, "حالا کلاس چندمی هستی؟", reply_markup=grade_markup(show_back_button=False))
    bot.register_next_step_handler(message, receive_grade)

def receive_grade(message):
    tid = message.from_user.id
    text = (message.text or "").strip()
    
    print(f"📝 دریافت پایه از کاربر {tid}: '{text}'")
    
    if text == "🔙 بازگشت به منوی اصلی":
        bot.send_message(tid, "بازگشت به منوی اصلی", reply_markup=main_menu_markup())
        if tid in pending_grade:
            pending_grade.pop(tid, None)
        if tid in changing_grade:
            changing_grade.pop(tid, None)
        return
    
    grade_map = {
        "7️⃣ هفتم": "7", "8️⃣ هشتم": "8", "9️⃣ نهم": "9", 
        "هفتم": "7", "هشتم": "8", "نهم": "9",
        "7": "7", "8": "8", "9": "9",
        "7️⃣": "7", "8️⃣": "8", "9️⃣": "9"
    }
    
    grade = grade_map.get(text)
    print(f"🔍 پایه تشخیص داده شده: {grade} از متن: '{text}'")
    
    if not grade:
        bot.send_message(tid, "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=grade_markup(show_back_button=(tid in changing_grade)))
        bot.register_next_step_handler(message, receive_grade)
        return
    
    update_grade(tid, grade)
    
    if tid in pending_grade:
        pending_grade.pop(tid, None)
        bot.send_message(tid, f"✅ ثبت‌نام کامل شد! پایهٔ شما {grade} ثبت شد.", reply_markup=main_menu_markup())
    elif tid in changing_grade:
        changing_grade.pop(tid, None)
        bot.send_message(tid, f"✅ پایهٔ شما به {grade} تغییر یافت.", reply_markup=main_menu_markup())
    else:
        bot.send_message(tid, f"✅ پایهٔ شما {grade} ثبت شد.", reply_markup=main_menu_markup())

@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    tid = message.from_user.id
    text = (message.text or "").strip()

    # چک کردن اسپم قبل از هر چیز
    if check_spam(tid):
        auto_ban_user(tid, "ارسال پیام‌های مکرر")
        bot.send_message(tid, "🚫 شما به دلیل اسپم بن شده‌اید!")
        return

    if is_banned(tid):
        remaining_time = get_remaining_ban_time(tid)
        if remaining_time > 0:
            bot.send_message(tid, f"🚫 شما به دلیل اسپم بن شده‌اید!\n⏰ زمان باقی‌مانده: {remaining_time//60} دقیقه")
        else:
            bot.send_message(tid, "🚫 شما از بات مسدود شده‌اید!")
        return

    print(f"📨 پیام از {tid}: '{text}'")

    with sessions_lock:
        has_session = tid in sessions
    
    if has_session:
        process_answer_in_session(message)
        return

    if message.from_user.id in ADMIN_ID:
        if text.startswith("+ "):
            try:
                parts = text[2:].rsplit(" ", 1)
                name = parts[0].strip()
                val = int(parts[1])
                tid_target = fullname_exists(name)
                if tid_target:
                    add_score(tid_target, val)
                    bot.send_message(tid, f"✅ {val} سکه به {name} اضافه شد.")
                else:
                    bot.send_message(tid, "کاربر یافت نشد.")
            except Exception:
                bot.send_message(tid, "فرمت اشتباه. مثال: + علی 100")
            return

        if text.startswith("- "):
            try:
                parts = text[2:].rsplit(" ", 1)
                name = parts[0].strip()
                val = int(parts[1])
                tid_target = fullname_exists(name)
                if tid_target:
                    subtract_score(tid_target, val)
                    bot.send_message(tid, f"✅ {val} سکه از {name} کم شد.")
                else:
                    bot.send_message(tid, "کاربر یافت نشد.")
            except Exception:
                bot.send_message(tid, "فرمت اشتباه. مثال: - علی 50")
            return

        if text.startswith("re "):
            try:
                name = text[3:].strip()
                if delete_user_by_fullname(name):
                    bot.send_message(tid, f"✅ کاربر {name} حذف شد.")
                else:
                    bot.send_message(tid, "❌ کاربر یافت نشد.")
            except:
                bot.send_message(tid, "خطا در حذف کاربر.")
            return

        if text.startswith("Ban "):
            try:
                name = text[4:].strip()
                if ban_user(name):
                    bot.send_message(tid, f"🔒 کاربر {name} بن شد.")
                else:
                    bot.send_message(tid, "❌ کاربر یافت نشد.")
            except:
                bot.send_message(tid, "خطا در بن کردن کاربر.")
            return

        if text.startswith("Unban "):
            try:
                name = text[6:].strip()
                if unban_user(name):
                    bot.send_message(tid, f"🔓 کاربر {name} آنبن شد.")
                else:
                    bot.send_message(tid, "❌ کاربر یافت نشد یا بن نیست.")
            except:
                bot.send_message(tid, "خطا در آنبن کردن کاربر.")
            return

        if text == "banned":
            banned_users = get_banned_users()
            if not banned_users:
                bot.send_message(tid, "❌ هیچ کاربری بن نشده است.")
                return
            
            message_text = "🔒 لیست کاربران بن شده:\n\n"
            for user_id, user_data in banned_users.items():
                message_text += f"👤 {user_data['fullname']}\n"
                message_text += f"🆔 آیدی: {user_id}\n"
                message_text += f"⏰ زمان بن: {user_data['banned_at']}\n"
                message_text += f"👮 بن شده توسط: {user_data['banned_by']}\n"
                message_text += f"📝 دلیل: {user_data.get('reason', 'نامشخص')}\n"
                message_text += "──────────────\n"
            
            bot.send_message(tid, message_text)
            return

        if text.startswith("A "):
            msg = text[2:].strip()
            ids = all_user_ids()
            sent = 0
            for user_id in ids:
                try:
                    if not is_banned(user_id):
                        bot.send_message(user_id, f"📢 پیام همگانی:\n{msg}")
                        sent += 1
                except:
                    pass
            bot.send_message(tid, f"✅ پیام به {sent} کاربر ارسال شد.")
            return

        if text == "player":
            all_users = get_all_users()
            if not all_users:
                bot.send_message(tid, "❌ هیچ کاربری ثبت‌نام نکرده است.")
                return
            
            chunk_size = 10
            for i in range(0, len(all_users), chunk_size):
                chunk = all_users[i:i + chunk_size]
                message_text = f"👥 لیست بازیکنان (بخش {i//chunk_size + 1}):\n\n"
                
                for j, user in enumerate(chunk, 1):
                    message_text += f"{i+j}. {user['fullname']}\n"
                    message_text += f"   🆔 آیدی: {user['id']}\n"
                    message_text += f"   📱 یوزرنیم: @{user['username']}\n"
                    message_text += f"   📚 پایه: {user['grade']}\n"
                    message_text += f"   💰 امتیاز: {user['score']}\n"
                    message_text += f"   📅 عضویت: {user['join_date']}\n"
                    message_text += "   ──────────────\n"
                
                try:
                    bot.send_message(tid, message_text)
                except Exception as e:
                    print(f"خطا در ارسال لیست کاربران: {e}")
            return

    if text == "🎮 شروع بازی":
        user = get_user(tid)
        if not user or not user[3]:
            bot.send_message(tid, "ابتدا ثبت‌نام و پایه‌ات را انتخاب کن (/start).")
            return
        bot.send_message(tid, "سطح را انتخاب کن:", reply_markup=level_markup())
        return

    if text in ["🟢 آسان 😌", "🟠 نرمال 😎", "🔴 سخت 😈"]:
        map_levels = {"🟢 آسان 😌": "easy", "🟠 نرمال 😎": "normal", "🔴 سخت 😈": "hard"}
        level_key = map_levels[text]
        user = get_user(tid)
        grade = user[3] if user else None
        if grade:
            success, message = start_quiz_for_user(tid, grade, level_key)
            if not success:
                bot.send_message(tid, message, reply_markup=main_menu_markup())
        else:
            bot.send_message(tid, "ابتدا پایه‌ات را انتخاب کن.", reply_markup=main_menu_markup())
        return

    if text == "🏆 رنکینگ":
        rows = top_users(10)
        if not rows:
            bot.send_message(tid, "هنوز بازیکنی ثبت نشده.", reply_markup=main_menu_markup())
            return
        txt = "🏆 رتبه‌بندی:\n\n"
        for i, (nm, sc) in enumerate(rows, 1):
            txt += f"{i}. {nm}: {sc} امتیاز\n"
        bot.send_message(tid, txt, reply_markup=main_menu_markup())
        return

    if text == "👤 اکانت":
        u = get_user(tid)
        if not u:
            bot.send_message(tid, "ابتدا ثبت‌نام کن (/start).")
            return
        bot.send_message(tid, f"👤 نام: {u[1]}\n📚 پایه: {u[3]}\n💰 امتیاز: {u[4]}", reply_markup=main_menu_markup())
        return

    if text == "💎 درخواست مثبت":
        s = get_score(tid)
        if s >= POSITIVE_THRESHOLD:
            subtract_score(tid, POSITIVE_THRESHOLD)
            bot.send_message(tid, f"✅ درخواست مثبت ثبت شد و {POSITIVE_THRESHOLD} سکه کم شد.", reply_markup=main_menu_markup())
            try:
                if ADMIN_ID:
                    user = get_user(tid)
                    if user:
                        fullname = user[1]
                        username = user[2] if user[2] else "ندارد"
                        for admin_id in ADMIN_ID:
                            bot.send_message(admin_id, f"📩 درخواست مثبت جدید:\n👤 نام کامل: {fullname}\n📱 یوزرنیم: @{username}\n🆔 آیدی: {tid}")
            except:
                pass
        else:
            bot.send_message(tid, f"❌ برای درخواست مثبت حداقل {POSITIVE_THRESHOLD} امتیاز لازم است.", reply_markup=main_menu_markup())
        return

    if text == "🛠 تغییر پایه":
        changing_grade[tid] = True
        bot.send_message(tid, "پایه جدید را انتخاب کن:", reply_markup=grade_markup(show_back_button=True))
        bot.register_next_step_handler(message, receive_grade)
        return

    if text == "📞 پشتیبانی":
        support_text = """
🤝 **پشتیبانی بات آموزشی**

📞 **آیدی پشتیبانی:**
@Mahyar015

✨ **ما اینجاییم تا کمک کنیم:**
• پاسخ به سوالات فنی
• راهنمایی در استفاده از بات
• گزارش مشکلات و باگ‌ها
• پیشنهادات و انتقادات

🚀 **با خیال راحت بازی کن، ما پشتیبان تو هستیم!**
        """
        bot.send_message(tid, support_text, reply_markup=main_menu_markup())
        return

    if text == "📚 راهنما":
        help_user_text = """
📚 **راهنمای کامل بات آموزشی**

🎮 **شروع بازی:**
- انتخاب پایه تحصیلی (هفتم، هشتم، نهم)
- انتخاب سطح (آسان، نرمال، سخت)
- پاسخ به 10 سوال در مدت زمان محدود

🏆 **سیستم امتیازدهی:**
- 🟢 آسان: 2 امتیاز برای هر پاسخ صحیح
- 🟠 نرمال: 5 امتیاز برای هر پاسخ صحیح  
- 🔴 سخت: 10 امتیاز برای هر پاسخ صحیح

📊 **منوهای اصلی:**
- 🎮 شروع بازی: شروع چالش جدید
- 🏆 رنکینگ: مشاهده برترین بازیکنان
- 👤 اکانت: اطلاعات حساب کاربری
- 💎 درخواست مثبت: ارسال درخواست به ادمین
- 🛠 تغییر پایه: تغییر پایه تحصیلی
- 📞 پشتیبانی: ارتباط با پشتیبانی
- 📚 راهنما: همین صفحه!

💡 **نکات مهم:**
- هر سوال 20 ثانیه زمان دارد
- امتیاز بر اساس سطح بازی محاسبه می‌شود
- برای درخواست مثبت حداقل 1000 امتیاز نیاز است
- ارسال پیام‌های مکرر منجر به بن شدن می‌شود
        """
        bot.send_message(tid, help_user_text, reply_markup=main_menu_markup())
        return

    if text == "🔙 بازگشت به منوی اصلی":
        bot.send_message(tid, "منوی اصلی:", reply_markup=main_menu_markup())
        return

    bot.send_message(tid, "لطفاً یکی از گزینه‌های منو را انتخاب کنید:", reply_markup=main_menu_markup())

# =================== اجرای بات ===================
if __name__ == "__main__":
    print("🎯 راه‌اندازی بات آموزشی فارسی روی Railway")
    print("=" * 60)
    
    if not os.path.exists(USERS_FILE):
        save_users({})
        print("✅ فایل کاربران ایجاد شد")
    if not os.path.exists(BANNED_USERS_FILE):
        save_banned_users({})
        print("✅ فایل کاربران بن شده ایجاد شد")
    if not os.path.exists(SPAM_TRACKER_FILE):
        save_spam_tracker({})
        print("✅ فایل ردیابی اسپم ایجاد شد")
    
    print("📁 بررسی فایل‌های سوالات:")
    for grade, file_path in QUESTIONS_FILES.items():
        if os.path.exists(file_path):
            print(f"✅ فایل سوالات پایه {grade}: {file_path}")
        else:
            print(f"❌ فایل سوالات پایه {grade} یافت نشد: {file_path}")
    
    print("🛡️ سیستم آنتی-اسپم فعال شد")
    print(f"   - حداکثر {SPAM_LIMIT} پیام در {SPAM_TIME_WINDOW} ثانیه")
    print(f"   - مدت بن: {SPAM_BAN_DURATION//3600} ساعت")
    
    print("✅ همه چیز آماده است!")
    print("📱 بات در حال گوش دادن به پیام‌ها...")
    
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"خطا در polling: {e}")
