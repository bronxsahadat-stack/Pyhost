# -*- coding: utf-8 -*-
# =====================================================================
#  ✨ PREMIUM HOST BOT ✨  (FIXED + COLORED BUTTONS EDITION)
#  Host & Run Telegram bots 24/7
#  ------------------------------------------------------------------
#  ✔ সব বাটনে কালার (Bot API 9.4: primary/success/danger)
#  ✔ পুরনো লাইব্রেরিতে crash করবে না (ikb()/kb() সেফ হেল্পার)
#  ✔ File upload limit চেক আসলেই কাজ করে
#  ✔ Speed & Ping এখন রিয়েল (CPU/RAM/Disk সহ)
#  ✔ ZIP আপলোড → auto extract + requirements.txt auto install
#  ✔ ছোটখাটো টাইপো/লজিক ফিক্স
#  ⚠️ শর্ত: pip install -U pyTelegramBotAPI
# =====================================================================
import atexit
from datetime import datetime, timedelta
import logging
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
import zipfile
from flask import Flask
from threading import Thread
import psutil
import telebot
from telebot import types

# --- Configurable ---
USDT_BDT_RATE = 120.0          # price reference (bKash/Nagad)

# --- Flask Keep Alive (uptime for hosting panels) ---
app = Flask("")

@app.route("/")
def home():
    return "✨ Premium Host Bot — Running 24/7"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    print("✅ Flask Keep-Alive server started.")

# =====================================================================
#  🎬 GIGAPUB REWARDED AD INTEGRATION
# =====================================================================
GIGA_PROJECT_ID = "8290"
GIGA_NEEDED = 0                 # কয়টা অ্যাড দেখলে ফ্রি এক্টিভেশন
GIGA_REWARD_HOURS = 0          # কয় ঘণ্টা ফ্রি হোস্টিং
GIGA_REWARD_PLAN_NAME = "🎬 AD FREE PLAN"

GIGA_WEBAPP_URL = "https://demositebbz.blogspot.com/"

# --- Configuration ---
TOKEN = "8815456004:AAH6MOOKf0Hggd3tgLRh5HcWcLdaLbaIfuE"
OWNER_ID = 8689170506
ADMIN_ID = 8689170506
YOUR_USERNAME = "@HASAN_BOT_DEV"
UPDATE_CHANNEL = ""

# --- bKash / Nagad Manual Payment Config (defaults — Admin Panel থেকে বদলানো যায়) ---
BKASH_NUMBER = "01820583511"
NAGAD_NUMBER = "01820583511"
PAY_REF = "HOSTBOT"

# --- Simple coupon codes: code -> discount % off the plan price ---
COUPONS = {
    # "WELCOME10": 10,
    # "EID50": 50,
}

PLAN_ICONS = {"pro": "⚡", "premium": "🌟", "business": "👑", "boss": "👑", "basic": "🔹", "vip": "💎"}

def plan_icon(name):
    n = (name or "").lower()
    for key, icon in PLAN_ICONS.items():
        if key in n:
            return icon
    return "📦"

# --- Folder setup ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_BOTS_DIR = os.path.join(BASE_DIR, "upload_bots")
DATA_DIR = os.path.join(BASE_DIR, "inf")
DATABASE_PATH = os.path.join(DATA_DIR, "bot_data.db")

FREE_USER_LIMIT = 0
SUBSCRIBED_USER_LIMIT = 150
ADMIN_LIMIT = 999
OWNER_LIMIT = float("inf")

os.makedirs(UPLOAD_BOTS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

bot = telebot.TeleBot(TOKEN)

bot_scripts = {}
user_subscriptions = {}
user_files = {}
active_users = set()
admin_ids = {ADMIN_ID, OWNER_ID}
bot_locked = False

# --- Malware / Suspicious detection ---
SUSPICIOUS_KEYWORDS = [b"ransomware", b"trojan", b"virus", b"malware",
                       b"backdoor", b"exploit", b"payload", b"botnet",
                       b"keylogger", b"rootkit"]

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# =====================================================================
#  🎨 COLORED BUTTON HELPERS (Bot API 9.4)
#  নতুন pyTelegramBotAPI থাকলে কালার দেখাবে; পুরনোটায় নিরাপদে ফলব্যাক।
# =====================================================================
try:
    types.InlineKeyboardButton("t", callback_data="t", style="primary")
    BTN_STYLE_SUPPORTED = True
except TypeError:
    BTN_STYLE_SUPPORTED = False
    logger.warning("⚠️ পুরনো pyTelegramBotAPI — কালার বাটনের জন্য চালান: pip install -U pyTelegramBotAPI")

def ikb(text, style=None, **kw):
    """Inline Keyboard Button (কালার সাপোর্টেড হলে style সহ)।"""
    if style and BTN_STYLE_SUPPORTED:
        return types.InlineKeyboardButton(text, style=style, **kw)
    return types.InlineKeyboardButton(text, **kw)

def kb(text, style=None, **kw):
    """Reply Keyboard Button (কালার সাপোর্টেড হলে style সহ)।"""
    if style and BTN_STYLE_SUPPORTED:
        return types.KeyboardButton(text, style=style, **kw)
    return types.KeyboardButton(text, **kw)

def build_ad_button():
    """Inline button that opens the GigaPub WebApp."""
    return ikb("🎬 Watch Ad", style="primary",
               web_app=types.WebAppInfo(url=GIGA_WEBAPP_URL))

# --- Button Layouts (🌐 ভাষা-ভিত্তিক লেবেল) ---
# প্রতিটা বাটনের একটা স্থায়ী "key" আছে — কালার আর হ্যান্ডলার সব key দিয়ে ম্যাপ হয়,
# দেখানো লেখাটা ইউজারের ভাষা অনুযায়ী বদলায়।
MENU_BUTTON_LABELS = {
    "free_host": {"bn": "💎 ফ্রি হোস্ট",        "en": "💎 𝗙𝗿𝗲𝗲 𝗛𝗼𝘀𝘁"},
    "buy_plan":  {"bn": "💳 প্ল্যান কিনুন",      "en": "💳 𝗕𝘂𝘆 𝗣𝗹𝗮𝗻"},
    "upload":    {"bn": "🚀 ফাইল আপলোড",       "en": "🚀 𝗨𝗽𝗹𝗼𝗮𝗱 𝗙𝗶𝗹𝗲"},
    "manage":    {"bn": "📁 ফাইল ম্যানেজ",      "en": "📁 𝗠𝗮𝗻𝗮𝗴𝗲 𝗙𝗶𝗹𝗲𝘀"},
    "support":   {"bn": "🎧 সাপোর্ট",          "en": "🎧 𝗦𝘂𝗽𝗽𝗼𝗿𝘁"},
    "updates":   {"bn": "📢 আপডেটস",           "en": "📢 𝗨𝗽𝗱𝗮𝘁𝗲𝘀"},
    "account":   {"bn": "👤 অ্যাকাউন্ট",        "en": "👤 𝗔𝗰𝗰𝗼𝘂𝗻𝘁"},
    "language":  {"bn": "🌐 ভাষা",             "en": "🌐 𝗟𝗮𝗻𝗴𝘂𝗮𝗴𝗲"},
    "stats":     {"bn": "📊 বট স্ট্যাটস",       "en": "📊 𝗕𝗼𝘁 𝗦𝘁𝗮𝘁𝘀"},
    "speed":     {"bn": "⚡ স্পিড ও পিং",      "en": "⚡ 𝗦𝗽𝗲𝗲𝗱 & 𝗣𝗶𝗻𝗴"},
    "admin":     {"bn": "🛡️ এডমিন প্যানেল",     "en": "🛡️ 𝗔𝗱𝗺𝗶𝗻 𝗣𝗮𝗻𝗲𝗹"},
}

USER_MENU_LAYOUT = [
    ["free_host", "buy_plan"],
    ["upload", "manage"],
    ["support", "updates"],
    ["account", "language"],
    ["stats", "speed"],
]
ADMIN_MENU_LAYOUT = [
    ["free_host", "buy_plan"],
    ["upload", "manage"],
    ["support", "updates"],
    ["account", "language"],
    ["speed", "admin"],
]

# কোন বাটনে কোন কালার (key দিয়ে — ভাষা বদলালেও কালার একই থাকবে)
# ৩টা কালারই আছে: primary 🔵  success 🟢  danger 🔴 — পছন্দমতো বদলে নিন
MAIN_BUTTON_STYLES = {
    "free_host": "success",   # 🟢
    "buy_plan":  "primary",   # 🔵
    "upload":    "primary",   # 🔵
    "manage":    "success",   # 🟢
    "support":   "danger",    # 🔴
    "updates":   "primary",   # 🔵
    "account":   "success",   # 🟢
    "language":  "danger",    # 🔴
    "stats":     "primary",   # 🔵
    "speed":     "danger",    # 🔴
    "admin":     "primary",   # 🔵
}

# --- Database Setup ---
DB_LOCK = threading.RLock()

def init_db():
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS subscriptions
                     (user_id INTEGER PRIMARY KEY, plan_name TEXT, expiry TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS user_files
                     (user_id INTEGER, file_name TEXT, file_type TEXT,
                      PRIMARY KEY (user_id, file_name))""")
        c.execute("""CREATE TABLE IF NOT EXISTS active_users
                     (user_id INTEGER PRIMARY KEY)""")
        c.execute("""CREATE TABLE IF NOT EXISTS admins
                     (user_id INTEGER PRIMARY KEY)""")
        c.execute("""CREATE TABLE IF NOT EXISTS plans
                     (plan_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT,
                      file_limit INTEGER, price TEXT, duration INTEGER, buy_link TEXT,
                      features TEXT)""")
        try:
            c.execute("ALTER TABLE plans ADD COLUMN features TEXT")
        except Exception:
            pass
        c.execute("""CREATE TABLE IF NOT EXISTS ad_rewards
                     (user_id INTEGER PRIMARY KEY, ad_count INTEGER)""")
        c.execute("""CREATE TABLE IF NOT EXISTS force_join
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, link TEXT, chat_ref TEXT)""")
        try:
            c.execute("ALTER TABLE force_join ADD COLUMN chat_ref TEXT")
        except Exception:
            pass
        c.execute("""CREATE TABLE IF NOT EXISTS pending_payments
                     (user_id INTEGER, plan_id INTEGER, method TEXT, txid TEXT,
                      PRIMARY KEY (user_id, plan_id))""")
        c.execute("""CREATE TABLE IF NOT EXISTS settings
                     (key TEXT PRIMARY KEY, value TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS accounts
                     (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0,
                      referred_by INTEGER, lang TEXT DEFAULT 'bn', lang_chosen INTEGER DEFAULT 0)""")
        try:
            c.execute("ALTER TABLE accounts ADD COLUMN lang_chosen INTEGER DEFAULT 0")
        except Exception:
            pass
        c.execute("""CREATE TABLE IF NOT EXISTS referrals
                     (referrer_id INTEGER, referred_id INTEGER PRIMARY KEY)""")
        c.execute("""CREATE TABLE IF NOT EXISTS redeem_codes
                     (code TEXT PRIMARY KEY, plan_id INTEGER, used_by INTEGER,
                      created_at TEXT)""")
        c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (OWNER_ID,))
        if ADMIN_ID != OWNER_ID:
            c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (ADMIN_ID,))
        conn.commit(); conn.close()
        logger.info("Database initialized.")
    except Exception as e:
        logger.error(f"DB init error: {e}")

def load_data():
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT user_id, plan_name, expiry FROM subscriptions")
        for row in c.fetchall():
            try:
                user_subscriptions[row[0]] = {"plan_name": row[1],
                                              "expiry": datetime.fromisoformat(row[2])}
            except ValueError:
                pass
        c.execute("SELECT user_id, file_name, file_type FROM user_files")
        for uid, fn, ft in c.fetchall():
            user_files.setdefault(uid, []).append((fn, ft))
        c.execute("SELECT user_id FROM active_users")
        active_users.update(r[0] for r in c.fetchall())
        c.execute("SELECT user_id FROM admins")
        admin_ids.update(r[0] for r in c.fetchall())
        conn.close()
        logger.info("Data loaded.")
    except Exception as e:
        logger.error(f"Load error: {e}")

init_db()
load_data()

# =====================================================================
#  AD-REWARD HELPERS
# =====================================================================
AD_CLAIM_COOLDOWN = 45
_last_claim = {}

def get_ad_progress(user_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT ad_count FROM ad_rewards WHERE user_id=?", (user_id,))
        row = c.fetchone(); conn.close()
        return row[0] if row else 0

def can_claim_ad(user_id):
    last = _last_claim.get(user_id, 0)
    elapsed = time.time() - last
    if elapsed < AD_CLAIM_COOLDOWN:
        return False, int(AD_CLAIM_COOLDOWN - elapsed)
    return True, 0

def grant_ad_reward(user_id):
    allowed, wait = can_claim_ad(user_id)
    if not allowed:
        return 0, False, wait
    _last_claim[user_id] = time.time()
    count = get_ad_progress(user_id) + 1
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO ad_rewards (user_id, ad_count) VALUES (?, ?)",
                  (user_id, count))
        conn.commit(); conn.close()
    if count >= GIGA_NEEDED:
        _activate_ad_reward(user_id)
        return count, True, 0
    return count, False, 0

def _activate_ad_reward(user_id):
    expiry = datetime.now() + timedelta(hours=GIGA_REWARD_HOURS)
    save_subscription(user_id, GIGA_REWARD_PLAN_NAME, expiry)
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("DELETE FROM ad_rewards WHERE user_id=?", (user_id,))
        conn.commit(); conn.close()
    try:
        bot.send_message(user_id,
            f"🎉 **অভিনন্দন!** 🎉\n━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ **{GIGA_NEEDED}টা অ্যাড সম্পন্ন!**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🤖 আপনার **{GIGA_REWARD_HOURS} ঘণ্টা ফ্রি হোস্টিং** আনলক হয়েছে!\n\n"
            f"👉 এখন **🚀 Upload File** চেপে আপনার বট হোস্ট করুন।",
            parse_mode="Markdown")
    except Exception:
        pass

def is_verified(user_id):
    if user_id in admin_ids or user_id == OWNER_ID:
        return True
    if user_id in user_subscriptions and user_subscriptions[user_id]["expiry"] > datetime.now():
        return True
    return get_ad_progress(user_id) >= GIGA_NEEDED

def show_ad_verification(chat_id, user_id):
    progress = get_ad_progress(user_id)
    left = max(0, GIGA_NEEDED - progress)
    pct = int((progress / GIGA_NEEDED) * 100) if GIGA_NEEDED else 100
    bar = "▰" * progress + "▱" * left
    txt = (f"{t(user_id,'ad_title')}\n━━━━━━━━━━━━━━━━━━━━━\n\n"
           f"{t(user_id,'ad_body', needed=GIGA_NEEDED)}\n\n"
           f"{t(user_id,'ad_progress', pct=pct, bar=bar)}\n"
           f"{t(user_id,'ad_watched', done=progress, needed=GIGA_NEEDED)}\n"
           f"{t(user_id,'ad_remaining', left=left)}\n"
           f"━━━━━━━━━━━━━━━━━━━━━\n\n"
           f"{t(user_id,'ad_cta')}\n\n"
           f"{t(user_id,'ad_note')}")
    mk = types.InlineKeyboardMarkup()
    mk.add(build_ad_button())
    mk.add(ikb("💳 Skip — Buy Plan", callback_data="view_plans_cb"))
    bot.send_message(chat_id, txt, reply_markup=mk, parse_mode="Markdown")

# =====================================================================
#  FORCE JOIN HELPERS
# =====================================================================
def get_force_join_channels():
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT rowid, link, chat_ref FROM force_join")
    rows = c.fetchall(); conn.close()
    return rows

def add_force_join_channel(link, chat_ref=None):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT INTO force_join (link, chat_ref) VALUES (?, ?)", (link, chat_ref))
        conn.commit(); conn.close()

def set_force_join_ref(rowid, chat_ref):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("UPDATE force_join SET chat_ref=? WHERE rowid=?", (chat_ref, rowid))
        conn.commit(); conn.close()

def remove_force_join_channel(idx):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT rowid, link FROM force_join")
        rows = c.fetchall()
        if 0 <= idx < len(rows):
            c.execute("DELETE FROM force_join WHERE rowid=?", (rows[idx][0],))
            conn.commit()
        conn.close()

def extract_username(link):
    if "t.me/" in link:
        u = link.split("t.me/")[1].split("/")[0].split("?")[0]
        if u.startswith("+") or u.startswith("joinchat"):
            return None
        return "@" + u if not u.startswith("@") else u
    return None

def check_force_join(user_id):
    if user_id in admin_ids or user_id == OWNER_ID:
        return True, []
    missing = []
    for rowid, link, chat_ref in get_force_join_channels():
        target = chat_ref if chat_ref else extract_username(link)
        if not target:
            continue
        try:
            m = bot.get_chat_member(target, user_id)
            if m.status not in ["member", "administrator", "creator"]:
                missing.append(link)
        except Exception:
            missing.append(link)
    return (len(missing) == 0), missing

def force_join_menu():
    mk = types.InlineKeyboardMarkup()
    channels = get_force_join_channels()
    for i, (rowid, link, chat_ref) in enumerate(channels):
        tag = "✅" if chat_ref else "⚠️"
        mk.add(ikb(f"{tag} {link}", callback_data=f"rmfjoin_{i}"))
    mk.add(ikb("➕ Add Channel", callback_data="addfjoin", style="success"))
    mk.add(ikb("🔙 Back", callback_data="back_admin"))
    return mk

def show_force_join_prompt(chat_id, user_id=None):
    text = "📢 **আমাদের চ্যানেলগুলোতে জয়েন করুন!**\n\n"
    text += "বট ব্যবহার করতে নিচের সব চ্যানেলে জয়েন করা প্রয়োজন:\n\n"
    mk = types.InlineKeyboardMarkup()
    for rowid, link, chat_ref in get_force_join_channels():
        mk.add(ikb("📢 Join Channel", url=link, style="primary"))
    mk.add(ikb("✅ 𝗜 𝗝𝗼𝗶𝗻𝗲𝗱 ✅", callback_data="verify_join", style="success"))
    bot.send_message(chat_id, text, reply_markup=mk, parse_mode="Markdown")

# =====================================================================
#  PRICE & PLAN HELPERS
# =====================================================================
def parse_price_to_bdt(price_str):
    price_clean = str(price_str).upper().strip()
    nums = re.findall(r"[-+]?\d*\.\d+|\d+", price_clean)
    if not nums:
        return "0", price_str
    val = float(nums[0])
    if "USDT" in price_clean or "$" in price_clean or "USD" in price_clean:
        bdt = int(val * USDT_BDT_RATE)
        return f"{bdt}", f"{val} USDT (~{bdt} BDT)"
    return f"{int(val)}", price_str

def add_plan_db(name, file_limit, price, duration, buy_link, features=""):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT INTO plans (name, file_limit, price, duration, buy_link, features) "
                  "VALUES (?, ?, ?, ?, ?, ?)", (name, file_limit, price, duration, buy_link, features))
        conn.commit(); conn.close()

def get_all_plans():
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT plan_id, name, file_limit, price, duration, buy_link, features FROM plans")
    plans = c.fetchall(); conn.close()
    return plans

def get_plan_by_id(plan_id):
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT plan_id, name, file_limit, price, duration, buy_link, features "
              "FROM plans WHERE plan_id=?", (plan_id,))
    plan = c.fetchone(); conn.close()
    return plan

def plan_features_list(features_str):
    if not features_str:
        return []
    parts = re.split(r"[•,|]", features_str)
    return [p.strip() for p in parts if p.strip()]

# =====================================================================
#  SETTINGS
# =====================================================================
def get_setting(key, default=None):
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone(); conn.close()
    return row[0] if row else default

def set_setting(key, value):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit(); conn.close()

def get_bkash_number():
    return get_setting("bkash_number", BKASH_NUMBER)

def get_nagad_number():
    return get_setting("nagad_number", NAGAD_NUMBER)

def get_plan_banner():
    return get_setting("plan_banner_file_id")

def get_orders_group():
    gid = get_setting("orders_group_id")
    return int(gid) if gid else None

def get_support_link():
    return get_setting("support_link", f"https://t.me/{YOUR_USERNAME.lstrip('@')}")

def get_update_channel():
    return get_setting("update_channel", UPDATE_CHANNEL)

def get_referral_reward():
    return float(get_setting("referral_reward", "0") or 0)

# =====================================================================
#  🎟️ REDEEM CODES
# =====================================================================
import random, string

def generate_redeem_code(plan_id, length=10):
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=length))
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT INTO redeem_codes (code, plan_id, used_by, created_at) VALUES (?, ?, NULL, ?)",
                  (code, plan_id, datetime.now().isoformat()))
        conn.commit(); conn.close()
    return code

def redeem_code_use(code, user_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT plan_id, used_by FROM redeem_codes WHERE code=?", (code,))
        row = c.fetchone()
        if not row or row[1] is not None:
            conn.close(); return None
        plan_id = row[0]
        c.execute("UPDATE redeem_codes SET used_by=? WHERE code=? AND used_by IS NULL", (user_id, code))
        changed = c.rowcount
        conn.commit(); conn.close()
    if changed == 0:
        return None
    plan = get_plan_by_id(plan_id)
    if not plan:
        return None
    _, name, limit, price, duration, _, __ = plan
    return (name, duration)

# =====================================================================
#  ACCOUNTS: balance, referrals, language
# =====================================================================
def ensure_account(user_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO accounts (user_id, balance, lang) VALUES (?, 0, 'bn')", (user_id,))
        conn.commit(); conn.close()

def get_account(user_id):
    ensure_account(user_id)
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT balance, referred_by, lang, lang_chosen FROM accounts WHERE user_id=?", (user_id,))
    row = c.fetchone(); conn.close()
    return {"balance": row[0] or 0, "referred_by": row[1], "lang": row[2] or "bn", "lang_chosen": row[3] or 0}

def add_balance(user_id, amount):
    ensure_account(user_id)
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("UPDATE accounts SET balance = balance + ? WHERE user_id=?", (amount, user_id))
        conn.commit(); conn.close()

def deduct_balance(user_id, amount):
    ensure_account(user_id)
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("UPDATE accounts SET balance = balance - ? WHERE user_id=?", (amount, user_id))
        conn.commit(); conn.close()

def set_user_lang(user_id, lang, mark_chosen=True):
    ensure_account(user_id)
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        if mark_chosen:
            c.execute("UPDATE accounts SET lang=?, lang_chosen=1 WHERE user_id=?", (lang, user_id))
        else:
            c.execute("UPDATE accounts SET lang=? WHERE user_id=?", (lang, user_id))
        conn.commit(); conn.close()

def get_user_lang(user_id):
    return get_account(user_id)["lang"]

def get_referral_count(user_id):
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (user_id,))
    n = c.fetchone()[0]; conn.close()
    return n

def register_referral(referrer_id, referred_id):
    if referrer_id == referred_id:
        return False
    ensure_account(referred_id)
    acc = get_account(referred_id)
    if acc["referred_by"]:
        return False
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT 1 FROM referrals WHERE referred_id=?", (referred_id,))
        if c.fetchone():
            conn.close(); return False
        c.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer_id, referred_id))
        c.execute("UPDATE accounts SET referred_by=? WHERE user_id=?", (referrer_id, referred_id))
        conn.commit(); conn.close()
    reward = get_referral_reward()
    if reward > 0:
        add_balance(referrer_id, reward)
    return True

def referral_link(user_id):
    return f"https://t.me/{YOUR_USERNAME.lstrip('@')}?start=ref_{user_id}"

# =====================================================================
#  🌐 LANGUAGE (বাংলা / English)
# =====================================================================
TEXTS = {
    "bn": {
        "welcome_title": "🎉 **অভিনন্দন!** 🎉",
        "welcome_greet": "✨ **স্বাগতম, {name}!**",
        "welcome_id": "🆔 **আপনার আইডি:** `{uid}`",
        "welcome_status": "🔰 **স্ট্যাটাস:** {status}",
        "welcome_files": "📁 **ফাইল:** `{used}` / `{limit}`",
        "welcome_body": "🤖 **সম্পূর্ণ ফ্রিতে আপনার বট হোস্ট করুন!**\nআপনার Python (.py) ও JS (.js) বট ২৪/৭ চালু রাখুন, যেকোনো সময়।",
        "welcome_menu": "👇 নিচের মেনু থেকে বেছে নিন:",
        "ad_title": "🔒 **𝗩𝗲𝗿𝗶𝗳𝗶𝗰𝗮𝘁𝗶𝗼𝗻 𝗥𝗲𝗾𝘂𝗶𝗿𝗲𝗱** 🔒",
        "ad_body": "🤖 **সম্পূর্ণ ফ্রিতে আপনার বট হোস্ট করতে** বট ব্যবহারের আগে আপনাকে **{needed}টা অ্যাড** দেখতে হবে।",
        "ad_progress": "📊 **Progress:** `{pct}%`\n`{bar}`",
        "ad_watched": "✅ দেখা হয়েছে: `{done}/{needed}`",
        "ad_remaining": "⏳ বাকি আছে: `{left}`",
        "ad_cta": "👇 **Watch Ad** বাটনে চাপুন এবং অ্যাডটি শেষ পর্যন্ত দেখুন।\nঅ্যাড শেষ হলে **রিওয়ার্ড অটো-এসাইন** হবে, আলাদা কোনো বাটন চাপতে হবে না।",
        "ad_note": "✨ প্রতিটা অ্যাডের মাঝে সামান্য সময় লাগবে — ধন্যবাদ ধৈর্য ধরার জন্য!",
        "account_title": "👤 **𝗔𝗰𝗰𝗼𝘂𝗻𝘁 𝗜𝗻𝗳𝗼**",
        "account_id": "🆔 আইডি: `{uid}`",
        "account_plan": "🔰 বর্তমান প্ল্যান: **{plan}**",
        "account_balance": "💰 ব্যালেন্স: `{bal} BDT`",
        "account_refs": "👥 রেফার করেছেন: `{count} জন`",
        "account_rate": "💵 প্রতি রেফারে পাবেন: `{rate} BDT`",
        "account_link": "🔗 **আপনার রেফার লিংক:**\n\n`{link}`\n",
        "account_share": "নিচের লিংক শেয়ার করে নতুন মানুষ আনলে ব্যালেন্স যোগ হবে।",
        "support_title": "🎧 **𝗦𝘂𝗽𝗽𝗼𝗿𝘁 𝗖𝗲𝗻𝘁𝗲𝗿**",
        "support_body": "🙋‍♂️ যেকোনো ধরনের সমস্যা, প্রশ্ন বা সাহায্যের জন্য আমাদের এডমিনের সাথে যোগাযোগ করতে নিচের বাটনে ক্লিক করুন।",
        "support_note": "📌 আমরা যথাসম্ভব দ্রুত উত্তর দেওয়ার চেষ্টা করি।",
        "support_btn": "💬 𝗖𝗼𝗻𝘁𝗮𝗰𝘁 𝗦𝘂𝗽𝗽𝗼𝗿𝘁",
        "updates_title": "📢 **𝗨𝗽𝗱𝗮𝘁𝗲𝘀 & 𝗡𝗲𝘄𝘀**",
        "updates_body": "✨ সকল ধরনের আপডেট, নতুন ফিচার ও ঘোষণা পেতে আমাদের আপডেট চ্যানেলে যুক্ত থাকুন।\n\nনিচের বাটনে ক্লিক করে জয়েন করুন:",
        "updates_btn": "📢 𝗝𝗼𝗶𝗻 𝗨𝗽𝗱𝗮𝘁𝗲𝘀 𝗖𝗵𝗮𝗻𝗻𝗲𝗹",
        "lang_choose": "🌐 **ভাষা বেছে নিন:**",
        "lang_set": "✅ ভাষা এখন **বাংলা** সেট হয়েছে।",
    },
    "en": {
        "welcome_title": "🎉 **Congratulations!** 🎉",
        "welcome_greet": "✨ **Welcome, {name}!**",
        "welcome_id": "🆔 **Your ID:** `{uid}`",
        "welcome_status": "🔰 **Status:** {status}",
        "welcome_files": "📁 **Files:** `{used}` / `{limit}`",
        "welcome_body": "🤖 **Host your bot 100% free!**\nKeep your Python (.py) and JS (.js) bots running 24/7, anytime.",
        "welcome_menu": "👇 Choose an option from the menu below:",
        "ad_title": "🔒 **𝗩𝗲𝗿𝗶𝗳𝗶𝗰𝗮𝘁𝗶𝗼𝗻 𝗥𝗲𝗾𝘂𝗶𝗿𝗲𝗱** 🔒",
        "ad_body": "🤖 **To host your bot for free**, you need to watch **{needed} ads** before using the bot.",
        "ad_progress": "📊 **Progress:** `{pct}%`\n`{bar}`",
        "ad_watched": "✅ Watched: `{done}/{needed}`",
        "ad_remaining": "⏳ Remaining: `{left}`",
        "ad_cta": "👇 Tap **Watch Ad** and watch it till the end.\nYour reward will be **auto-assigned** once it's done — no extra button to press.",
        "ad_note": "✨ Each ad needs a short moment to unlock the next one — thanks for your patience!",
        "account_title": "👤 **𝗔𝗰𝗰𝗼𝘂𝗻𝘁 𝗜𝗻𝗳𝗼**",
        "account_id": "🆔 ID: `{uid}`",
        "account_plan": "🔰 Current Plan: **{plan}**",
        "account_balance": "💰 Balance: `{bal} BDT`",
        "account_refs": "👥 Referrals: `{count} people`",
        "account_rate": "💵 You earn per referral: `{rate} BDT`",
        "account_link": "🔗 **Your referral link:**\n\n`{link}`\n",
        "account_share": "Share the link below — your balance grows with every new person who joins.",
        "support_title": "🎧 **𝗦𝘂𝗽𝗽𝗼𝗿𝘁 𝗖𝗲𝗻𝘁𝗲𝗿**",
        "support_body": "🙋‍♂️ For any issue, question, or help, tap the button below to reach our admin.",
        "support_note": "📌 We try to reply as quickly as possible.",
        "support_btn": "💬 𝗖𝗼𝗻𝘁𝗮𝗰𝘁 𝗦𝘂𝗽𝗽𝗼𝗿𝘁",
        "updates_title": "📢 **𝗨𝗽𝗱𝗮𝘁𝗲𝘀 & 𝗡𝗲𝘄𝘀**",
        "updates_body": "✨ Stay in our updates channel for every new feature and announcement.\n\nTap the button below to join:",
        "updates_btn": "📢 𝗝𝗼𝗶𝗻 𝗨𝗽𝗱𝗮𝘁𝗲𝘀 𝗖𝗵𝗮𝗻𝗻𝗲𝗹",
        "lang_choose": "🌐 **Choose your language:**",
        "lang_set": "✅ Language set to **English**.",
    },
}

def t(user_id, key, **kw):
    lang = get_user_lang(user_id)
    txt = TEXTS.get(lang, TEXTS["bn"]).get(key, TEXTS["bn"].get(key, key))
    return txt.format(**kw) if kw else txt

def delete_plan_db(plan_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("DELETE FROM plans WHERE plan_id=?", (plan_id,))
        conn.commit(); conn.close()

def save_subscription(user_id, plan_name, expiry):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO subscriptions (user_id, plan_name, expiry) "
                  "VALUES (?, ?, ?)", (user_id, plan_name, expiry.isoformat()))
        conn.commit(); conn.close()
    user_subscriptions[user_id] = {"plan_name": plan_name, "expiry": expiry}

def activate_user_plan(user_id, plan_name, days, notify=True):
    expiry = datetime.now() + timedelta(days=days)
    save_subscription(user_id, plan_name, expiry)
    if notify:
        try:
            bot.send_message(user_id,
                f"🎉 **অভিনন্দন!** 🎉\n━━━━━━━━━━━━━━━━━━━\n"
                f"✨ আপনার **{plan_name}** প্ল্যান সফলভাবে **এক্টিভ** হয়েছে!\n\n"
                f"⏳ মেয়াদ: **{days} দিন**\n📅 শেষ হবে: `{expiry.strftime('%d %b %Y, %I:%M %p')}`\n"
                f"━━━━━━━━━━━━━━━━━━━\n\n"
                f"👉 এখন **🚀 Upload File** চেপে আপনার বট হোস্ট করুন!",
                parse_mode="Markdown")
        except Exception:
            pass

def remove_subscription_db(user_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("DELETE FROM subscriptions WHERE user_id=?", (user_id,))
        conn.commit(); conn.close()
    user_subscriptions.pop(user_id, None)

# =====================================================================
#  FILE / SCRIPT HELPERS
# =====================================================================
def get_user_folder(user_id):
    folder = os.path.join(UPLOAD_BOTS_DIR, str(user_id))
    os.makedirs(folder, exist_ok=True)
    return folder

def get_user_file_limit(user_id):
    if user_id == OWNER_ID: return OWNER_LIMIT
    if user_id in admin_ids: return ADMIN_LIMIT
    if user_id in user_subscriptions and user_subscriptions[user_id]["expiry"] > datetime.now():
        return SUBSCRIBED_USER_LIMIT
    return FREE_USER_LIMIT

def get_user_file_count(user_id):
    return len(user_files.get(user_id, []))

def is_bot_running(owner_id, file_name):
    skey = f"{owner_id}_{file_name}"
    info = bot_scripts.get(skey)
    if info and info.get("process"):
        try:
            proc = psutil.Process(info["process"].pid)
            running = proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
            if not running:
                _close_log(info)
                bot_scripts.pop(skey, None)
            return running
        except psutil.NoSuchProcess:
            _close_log(info)
            bot_scripts.pop(skey, None)
            return False
        except Exception:
            return False
    return False

def _close_log(info):
    if info and "log_file" in info and hasattr(info["log_file"], "close") \
            and not info["log_file"].closed:
        try:
            info["log_file"].close()
        except Exception:
            pass

def kill_process_tree(info):
    try:
        _close_log(info)
        proc = info.get("process")
        if proc and getattr(proc, "pid", None):
            try:
                parent = psutil.Process(proc.pid)
                for child in parent.children(recursive=True):
                    try: child.terminate()
                    except Exception: pass
                try: parent.terminate()
                except Exception: pass
            except Exception: pass
    except Exception as e:
        logger.error(f"kill error: {e}")

TELEGRAM_MODULES = {
    "telebot": "pyTelegramBotAPI", "telegram": "python-telegram-bot",
    "python_telegram_bot": "python-telegram-bot", "aiogram": "aiogram",
    "pyrogram": "pyrogram", "telethon": "telethon", "bs4": "beautifulsoup4",
    "requests": "requests", "pillow": "Pillow", "cv2": "opencv-python",
    "flask": "Flask", "psutil": "psutil",
}

def monitor_and_guide_error(process, log_path, owner_id, file_name, msg_obj):
    time.sleep(3)
    if process.poll() is not None:
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                log = f.read()
            m_py = re.search(r"(?:ModuleNotFoundError|ImportError): No module named '(.+?)'", log)
            m_js = re.search(r"Cannot find module '(.+?)'", log)
            missing = None
            if m_py: missing = m_py.group(1).split(".")[0].strip("'\"")
            elif m_js: missing = m_js.group(1).split("/")[0].strip("'\"")
            if missing:
                pkg = TELEGRAM_MODULES.get(missing.lower(), missing)
                ext = os.path.splitext(file_name)[1].lower()
                cmd = f"npm install {pkg}" if ext == ".js" else f"pip install {pkg}"
                mk = types.InlineKeyboardMarkup()
                mk.add(ikb(f"📦 Install {pkg}", style="primary",
                           callback_data=f"instmod_{owner_id}_{missing}_{file_name}"))
                mk.add(ikb("📄 View Error Logs",
                           callback_data=f"viewlog_{owner_id}_{file_name}"))
                bot.reply_to(msg_obj,
                    f"⚠️ **ফাইল রান হতে সমস্যা!**\n📄 **File:** `{file_name}`\n"
                    f"❌ মিসিং মডিউল: `{missing}`\n💻 **কমান্ড:** `{cmd}`",
                    reply_markup=mk, parse_mode="Markdown")
            else:
                mk = types.InlineKeyboardMarkup()
                mk.add(ikb("📄 View Error Logs",
                           callback_data=f"viewlog_{owner_id}_{file_name}"))
                bot.reply_to(msg_obj, "⚠️ **আপনার কোডে ভুল পাওয়া গেছে!**\n\n📄 View Logs বাটনে ক্লিক করুন।",
                             reply_markup=mk, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"log check err: {e}")

def run_script(path, owner_id, ufolder, file_name, msg_obj, is_js=False):
    skey = f"{owner_id}_{file_name}"
    try:
        run_cwd = os.path.dirname(path) if os.path.dirname(path) else ufolder
        log_path = os.path.join(run_cwd, f"{os.path.splitext(os.path.basename(file_name))[0]}.log")
        logf = open(log_path, "w", encoding="utf-8", errors="ignore")
        cmd = ["node", path] if is_js else [sys.executable, path]
        proc = subprocess.Popen(cmd, cwd=run_cwd, stdout=logf, stderr=logf,
                                stdin=subprocess.PIPE)
        bot_scripts[skey] = {"process": proc, "log_file": logf, "file_name": file_name,
                             "script_owner_id": owner_id, "start_time": datetime.now(),
                             "user_folder": run_cwd, "type": "js" if is_js else "py",
                             "script_key": skey}
        bot.reply_to(msg_obj,
                     f"🚀 **Script Started!**\n📄 File: `{file_name}`\n🆔 PID: `{proc.pid}`",
                     parse_mode="Markdown")
        threading.Thread(target=monitor_and_guide_error,
                         args=(proc, log_path, owner_id, file_name, msg_obj)).start()
    except Exception as e:
        bot.reply_to(msg_obj, f"❌ Error running script: {str(e)}")

def save_user_file(user_id, file_name, file_type="py"):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO user_files (user_id, file_name, file_type) "
                  "VALUES (?, ?, ?)", (user_id, file_name, file_type))
        conn.commit(); conn.close()
        user_files.setdefault(user_id, [])
        user_files[user_id] = [(fn, ft) for fn, ft in user_files[user_id] if fn != file_name]
        user_files[user_id].append((file_name, file_type))

def remove_user_file_db(user_id, file_name):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("DELETE FROM user_files WHERE user_id=? AND file_name=?", (user_id, file_name))
        conn.commit(); conn.close()
        if user_id in user_files:
            user_files[user_id] = [f for f in user_files[user_id] if f[0] != file_name]

def add_active_user(user_id):
    active_users.add(user_id)
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO active_users (user_id) VALUES (?)", (user_id,))
        conn.commit(); conn.close()

# =====================================================================
#  📦 ZIP HELPERS (নতুন — আগে zip আপলোড হলেও কিছুই হতো না)
# =====================================================================
ENTRY_CANDIDATES = ["main.py", "bot.py", "app.py", "index.py",
                    "index.js", "main.js", "bot.js", "app.js", "server.js"]

def safe_extract_zip(zip_path, dest_dir):
    """Path traversal সুরক্ষাসহ zip extract।"""
    os.makedirs(dest_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        for member in z.namelist():
            clean = member.replace("\\", "/")
            if clean.startswith("/") or ".." in clean.split("/"):
                continue  # বিপজ্জনক পাথ বাদ
            z.extract(member, dest_dir)

def detect_entry_file(folder):
    for name in ENTRY_CANDIDATES:
        for root, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs if d != "__pycache__" and not d.startswith(".")]
            if name in files:
                return os.path.relpath(os.path.join(root, name), folder)
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d != "__pycache__" and not d.startswith(".")]
        for f in sorted(files):
            if f.endswith((".py", ".js")):
                return os.path.relpath(os.path.join(root, f), folder)
    return None

def find_requirements(folder):
    for root, dirs, files in os.walk(folder):
        if "requirements.txt" in files:
            return os.path.join(root, "requirements.txt")
    return None

# =====================================================================
#  MENUS (🎨 কালার সহ)
# =====================================================================
def create_main_menu(user_id):
    lang = get_user_lang(user_id)
    layout = ADMIN_MENU_LAYOUT if user_id in admin_ids else USER_MENU_LAYOUT
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for row in layout:
        mk.add(*[kb(MENU_BUTTON_LABELS[key][lang], style=MAIN_BUTTON_STYLES.get(key))
                 for key in row])
    return mk

def admin_panel_inline():
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(ikb("➕ Add Plan", callback_data="add_plan_init", style="success"),
           ikb("🗑️ Manage Plans", callback_data="manage_plans"))
    mk.add(ikb("💎 Add Subscription", callback_data="add_subscription", style="success"),
           ikb("❌ Remove Sub", callback_data="remove_subscription", style="danger"))
    mk.add(ikb("📢 Force Join", callback_data="force_join_menu"),
           ikb("📣 Broadcast", callback_data="broadcast", style="primary"))
    mk.add(ikb("🔐 Lock/Unlock", callback_data="toggle_lock", style="danger"),
           ikb("📊 Stats", callback_data="stats"))
    mk.add(ikb("💳 bKash Number", callback_data="set_bkash_num"),
           ikb("💳 Nagad Number", callback_data="set_nagad_num"))
    mk.add(ikb("🖼️ Plan Banner", callback_data="set_plan_banner"),
           ikb("👥 Orders Group", callback_data="set_orders_group"))
    mk.add(ikb("🎯 Referral Reward", callback_data="set_ref_reward"),
           ikb("💬 Support Link", callback_data="set_support_link"))
    mk.add(ikb("📢 Update Channel", callback_data="set_update_channel"),
           ikb("🎟️ Generate Code", callback_data="gen_redeem_code", style="primary"))
    return mk

# =====================================================================
#  CORE LOGIC
# =====================================================================
def send_welcome(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    name = message.from_user.first_name
    if bot_locked and user_id not in admin_ids:
        bot.send_message(chat_id, "⚠️ Bot is temporarily locked."); return
    add_active_user(user_id)
    ensure_account(user_id)

    joined, _ = check_force_join(user_id)
    if not joined:
        show_force_join_prompt(chat_id); return

    acc = get_account(user_id)
    if not acc.get("lang_chosen"):
        show_language_onboarding(chat_id, user_id)
        return

    if user_id == OWNER_ID: status = "👑 Owner"
    elif user_id in admin_ids: status = "🛡️ Admin"
    elif user_id in user_subscriptions and user_subscriptions[user_id]["expiry"] > datetime.now():
        sub = user_subscriptions[user_id]
        hrs = max(0, int((sub["expiry"] - datetime.now()).total_seconds() // 3600))
        status = f"💎 {sub.get('plan_name','Premium')} Active ({hrs}h left)"
    else: status = "🆓 No Active Plan"

    txt = (f"{t(user_id,'welcome_title')}\n━━━━━━━━━━━━━━━━━━━━━\n"
           f"{t(user_id,'welcome_greet', name=name)}\n━━━━━━━━━━━━━━━━━━━━━\n"
           f"{t(user_id,'welcome_id', uid=user_id)}\n{t(user_id,'welcome_status', status=status)}\n"
           f"{t(user_id,'welcome_files', used=get_user_file_count(user_id), limit=get_user_file_limit(user_id))}\n"
           f"━━━━━━━━━━━━━━━━━━━━━\n\n"
           f"{t(user_id,'welcome_body')}\n\n"
           f"{t(user_id,'welcome_menu')}")
    bot.send_message(chat_id, txt, reply_markup=create_main_menu(user_id), parse_mode="Markdown")

def show_language_onboarding(chat_id, user_id):
    mk = types.InlineKeyboardMarkup()
    mk.add(ikb("🇧🇩 বাংলা", callback_data="onboard_lang_bn", style="success"),
           ikb("🇬🇧 English", callback_data="onboard_lang_en", style="primary"))
    bot.send_message(chat_id,
        "🌐 **Please choose your language / আপনার ভাষা বেছে নিন:**",
        reply_markup=mk, parse_mode="Markdown")

def logic_free_host(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    joined, _ = check_force_join(user_id)
    if not joined:
        show_force_join_prompt(chat_id); return
    if user_id in user_subscriptions and user_subscriptions[user_id]["expiry"] > datetime.now():
        sub = user_subscriptions[user_id]
        hrs = max(0, int((sub["expiry"] - datetime.now()).total_seconds() // 3600))
        mk = types.InlineKeyboardMarkup()
        mk.add(ikb("🚀 Upload File Now", callback_data="confirm_plan_upload", style="success"))
        bot.send_message(chat_id,
            f"💎 **আপনার এক্টিভ হোস্টিং আছে!**\n📌 Plan: `{sub.get('plan_name')}`\n"
            f"⏱️ Remaining: `{hrs} ঘণ্টা`\n\nআপনি এখন **🚀 Upload File** চেপে বট হোস্ট করতে পারবেন।",
            reply_markup=mk, parse_mode="Markdown")
        return
    show_ad_verification(chat_id, user_id)

def user_current_plan_label(user_id):
    if user_id in user_subscriptions and user_subscriptions[user_id]["expiry"] > datetime.now():
        return user_subscriptions[user_id].get("plan_name", "Premium")
    return "FREE"

def logic_view_plans(msg_or_call):
    chat_id = msg_or_call.chat.id if isinstance(msg_or_call, telebot.types.Message) \
              else msg_or_call.message.chat.id
    user_id = msg_or_call.from_user.id
    plans = get_all_plans()
    if not plans:
        bot.send_message(chat_id, "ℹ️ বর্তমানে কোনো প্ল্যান নেই।", parse_mode="Markdown"); return

    lines = ["🚀 **Premium Plans**",
             f"🟢 বর্তমান: **{user_current_plan_label(user_id)}**",
             "👇 বেছে নিন:", ""]
    for p in plans:
        pid, name, limit, price, duration, buy_link, features = p
        feats = plan_features_list(features)
        short = feats[:4]
        extra = len(feats) - len(short)
        feat_txt = " • ".join(short) if short else f"{limit} Bot(s) • {duration} Days"
        if extra > 0:
            feat_txt += f" • +{extra} more"
        lines.append(f"{plan_icon(name)} **{name}:** {feat_txt}")
    text = "\n".join(lines)

    mk = types.InlineKeyboardMarkup(row_width=1)
    for p in plans:
        pid, name, limit, price, duration, buy_link, features = p
        bdt, fmt = parse_price_to_bdt(price)
        label = f"{plan_icon(name)} {name} — {bdt}৳/{duration}দিন"
        mk.add(ikb(label, callback_data=f"buyplan_{pid}", style="primary"))

    banner = get_plan_banner()
    if banner:
        caption = text if len(text) <= 1020 else text[:1017] + "..."
        try:
            bot.send_photo(chat_id, banner, caption=caption, reply_markup=mk, parse_mode="Markdown")
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=mk, parse_mode="Markdown")

def show_order_summary(chat_id, message_id, pid):
    plan = get_plan_by_id(pid)
    if not plan:
        bot.send_message(chat_id, "❌ Plan not found!"); return
    _, name, limit, price, duration, buy_link, features = plan
    bdt, fmt = parse_price_to_bdt(price)
    feats = plan_features_list(features)
    if not feats:
        feats = [f"{limit} Bot(s) hosting", f"{duration} Days validity"]
    feat_block = "\n".join(f"•  {f}" for f in feats)

    text = (f"🛒 **𝗢𝗿𝗱𝗲𝗿 𝗦𝘂𝗺𝗺𝗮𝗿𝘆**\n━━━━━━━━━━━━━━━━━━━\n"
            f"📦 **{name} Plan**  |  ⏱️ {duration} Days\n💰 **{bdt} BDT**\n\n"
            f"✨ **Features:**\n{feat_block}\n\n"
            f"👇 পেমেন্ট মেথড বেছে নিন:")

    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(ikb("💳 bKash", callback_data=f"buy_bkash_{pid}", style="success"),
           ikb("💳 Nagad", callback_data=f"buy_nagad_{pid}", style="success"))
    mk.add(ikb("💰 Pay with Balance", callback_data=f"pay_balance_{pid}", style="primary"))
    mk.add(ikb("🎟️ Redeem Code", callback_data=f"coupon_{pid}"))
    mk.add(ikb("◀️ Back", callback_data="view_plans_cb"))

    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=mk, parse_mode="Markdown")
    except Exception:
        bot.send_message(chat_id, text, reply_markup=mk, parse_mode="Markdown")

def logic_upload(message):
    user_id = message.from_user.id
    joined, _ = check_force_join(user_id)
    if not joined:
        show_force_join_prompt(message.chat.id); return
    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, "⚠️ Bot is locked."); return
    if not is_verified(user_id):
        show_ad_verification(message.chat.id, user_id); return
    pname = "None"
    if user_id in admin_ids or user_id == OWNER_ID:
        pname = "Admin/Owner Unlimited"
    elif user_id in user_subscriptions and user_subscriptions[user_id]["expiry"] > datetime.now():
        pname = user_subscriptions[user_id].get("plan_name", "Premium")
    mk = types.InlineKeyboardMarkup()
    mk.add(ikb(f"🟢 Continue with {pname}", callback_data="confirm_plan_upload", style="success"))
    bot.reply_to(message,
                 f"🔰 **Active Plan:** `{pname}`\n📁 **Files:** `{get_user_file_count(user_id)}` / "
                 f"`{get_user_file_limit(user_id)}`\n\nফাইল আপলোড চালু করতে নিচের বাটনে ক্লিক করুন:",
                 reply_markup=mk, parse_mode="Markdown")

def logic_check_files(message):
    user_id = message.from_user.id
    if not is_verified(user_id):
        show_ad_verification(message.chat.id, user_id); return
    flist = user_files.get(user_id, [])
    if not flist:
        bot.reply_to(message, "📂 **Your Uploaded Files:**\n\n*(No files yet)*", parse_mode="Markdown"); return
    mk = types.InlineKeyboardMarkup(row_width=1)
    for fn, ft in sorted(flist):
        running = is_bot_running(user_id, fn)
        icon = "🟢 Running" if running else "🔴 Stopped"
        mk.add(ikb(f"📄 {fn} ({ft}) - {icon}", callback_data=f"file_{user_id}_{fn}"))
    bot.reply_to(message, "📁 **Manage Your Files:**", reply_markup=mk, parse_mode="Markdown")

def logic_support(message):
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    markup.add(ikb(t(user_id, "support_btn"), url=get_support_link(), style="primary"))
    bot.reply_to(message,
        f"{t(user_id,'support_title')}\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{t(user_id,'support_body')}\n\n"
        f"{t(user_id,'support_note')}",
        reply_markup=markup, parse_mode="Markdown")

def logic_updates(message):
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    markup.add(ikb(t(user_id, "updates_btn"), url=get_update_channel(), style="primary"))
    bot.reply_to(message,
        f"{t(user_id,'updates_title')}\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{t(user_id,'updates_body')}",
        reply_markup=markup, parse_mode="Markdown")

def logic_account(message):
    user_id = message.from_user.id
    acc = get_account(user_id)
    plan = user_current_plan_label(user_id)
    ref_count = get_referral_count(user_id)
    rate = get_referral_reward()
    txt = (f"{t(user_id,'account_title')}\n━━━━━━━━━━━━━━━━━━━━━\n"
           f"{t(user_id,'account_id', uid=user_id)}\n"
           f"{t(user_id,'account_plan', plan=plan)}\n"
           f"{t(user_id,'account_balance', bal=round(acc['balance'],2))}\n"
           f"{t(user_id,'account_refs', count=ref_count)}\n"
           f"{t(user_id,'account_rate', rate=rate)}\n"
           f"━━━━━━━━━━━━━━━━━━━━━\n"
           f"{t(user_id,'account_link', link=referral_link(user_id))}\n"
           f"{t(user_id,'account_share')}")
    bot.reply_to(message, txt, parse_mode="Markdown")

def logic_language(message):
    user_id = message.from_user.id
    mk = types.InlineKeyboardMarkup()
    mk.add(ikb("🇧🇩 বাংলা", callback_data="lang_bn", style="success"),
           ikb("🇬🇧 English", callback_data="lang_en", style="primary"))
    bot.reply_to(message, t(user_id, "lang_choose"), reply_markup=mk, parse_mode="Markdown")

# ⚡ রিয়েল Speed & Ping (আগে hardcoded "12 ms" ছিল)
def logic_speed(message):
    start_t = time.time()
    m = bot.reply_to(message, "⏱️ পিং মাপা হচ্ছে...")
    ping_ms = round((time.time() - start_t) * 1000)
    try:
        cpu = psutil.cpu_percent(interval=0.2)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        txt = (f"⚡ **𝗦𝗽𝗲𝗲𝗱 & 𝗣𝗶𝗻𝗴**\n━━━━━━━━━━━━━━━━━━━━━\n"
               f"📶 **Bot Latency:** `{ping_ms} ms`\n"
               f"🖥️ **CPU:** `{cpu}%`\n"
               f"🧠 **RAM:** `{ram.percent}%` ({ram.used // (1024**2)}MB / {ram.total // (1024**2)}MB)\n"
               f"💾 **Disk:** `{disk.percent}%`\n"
               f"🤖 **Running Scripts:** `{len(bot_scripts)}`")
    except Exception:
        txt = f"⚡ **Bot Latency:** `{ping_ms} ms`"
    try:
        bot.edit_message_text(txt, m.chat.id, m.message_id, parse_mode="Markdown")
    except Exception:
        pass

# =====================================================================
#  DOCUMENT UPLOAD (✔ লিমিট চেক + ✔ ZIP সাপোর্ট ফিক্সড)
# =====================================================================
@bot.message_handler(content_types=["document"])
def handle_doc(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    doc = message.document
    joined, _ = check_force_join(user_id)
    if not joined:
        show_force_join_prompt(chat_id); return
    if not is_verified(user_id):
        show_ad_verification(chat_id, user_id); return

    # ✔ ফাইল লিমিট এঞ্ফোর্স (আগের কোডে চেকই ছিল না)
    limit = get_user_file_limit(user_id)
    if get_user_file_count(user_id) >= limit:
        mk = types.InlineKeyboardMarkup()
        mk.add(ikb("💳 Buy Plan", callback_data="view_plans_cb", style="primary"))
        mk.add(ikb("💎 Free Host (Ads)", callback_data="free_host_cb", style="success"))
        bot.reply_to(message,
            f"⚠️ **ফাইল লিমিট শেষ!**\n📁 আপনার সর্বোচ্চ লিমিট: `{limit}` টা ফাইল।\n\n"
            f"পুরনো ফাইল ডিলিট করুন অথবা প্ল্যান নিন।",
            reply_markup=mk, parse_mode="Markdown")
        return

    fname = doc.file_name
    ext = os.path.splitext(fname)[1].lower()
    if ext not in [".py", ".js", ".zip"]:
        bot.reply_to(message, "⚠️ শুধু `.py`, `.js`, `.zip` সাপোর্টেড!"); return
    try:
        wait = bot.reply_to(message, f"⏳ Downloading `{fname}`...", parse_mode="Markdown")
        finfo = bot.get_file(doc.file_id)
        content = bot.download_file(finfo.file_path)
        if ext == ".py" and user_id != OWNER_ID:
            sample = content[:4096].decode("utf-8", errors="ignore").lower()
            for kw in SUSPICIOUS_KEYWORDS:
                if kw.decode("utf-8") in sample:
                    bot.edit_message_text("🚨 **Security Alert:** Suspicious content.",
                                          chat_id, wait.message_id, parse_mode="Markdown")
                    return
        ufolder = get_user_folder(user_id)
        path = os.path.join(ufolder, fname)
        with open(path, "wb") as f:
            f.write(content)

        if ext == ".zip":
            bot.edit_message_text(f"📦 Extracting `{fname}`...", chat_id, wait.message_id,
                                  parse_mode="Markdown")
            extract_dir = os.path.join(ufolder, os.path.splitext(fname)[0] + "_src")
            safe_extract_zip(path, extract_dir)
            try:
                os.remove(path)  # extract হয়ে গেলে zip ফাইলটা রাখার দরকার নেই
            except Exception:
                pass

            entry = detect_entry_file(extract_dir)
            if not entry:
                bot.send_message(chat_id,
                    "❌ ZIP-এর ভেতরে কোনো `.py` বা `.js` ফাইল পাইনি!",
                    parse_mode="Markdown")
                return

            entry_is_js = entry.lower().endswith(".js")
            save_user_file(user_id, f"{os.path.splitext(fname)[0]}_src/{entry}",
                           "js" if entry_is_js else "py")

            req_path = find_requirements(extract_dir)
            if req_path and not entry_is_js:
                bot.send_message(chat_id, "📦 `requirements.txt` পাওয়া গেছে — প্যাকেজ ইনস্টল হচ্ছে...",
                                 parse_mode="Markdown")
                def install_then_run():
                    subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_path],
                                   capture_output=True, text=True)
                    run_script(os.path.join(extract_dir, entry), user_id, ufolder,
                               f"{os.path.splitext(fname)[0]}_src/{entry}", message, entry_is_js)
                threading.Thread(target=install_then_run).start()
            else:
                threading.Thread(target=run_script,
                                 args=(os.path.join(extract_dir, entry), user_id, ufolder,
                                       f"{os.path.splitext(fname)[0]}_src/{entry}", message, entry_is_js)).start()

            bot.edit_message_text(f"✅ **ZIP `{fname}` extract হয়ে রান হচ্ছে!**\n📄 Entry: `{entry}`",
                                  chat_id, wait.message_id, parse_mode="Markdown")
            return

        bot.edit_message_text(f"✅ **File `{fname}` uploaded!**",
                              chat_id, wait.message_id, parse_mode="Markdown")
        if ext == ".js":
            save_user_file(user_id, fname, "js")
            threading.Thread(target=run_script,
                             args=(path, user_id, ufolder, fname, message, True)).start()
        elif ext == ".py":
            save_user_file(user_id, fname, "py")
            threading.Thread(target=run_script,
                             args=(path, user_id, ufolder, fname, message, False)).start()
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

# =====================================================================
#  CALLBACKS
# =====================================================================
@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    user_id = call.from_user.id
    data = call.data

    if data == "view_plans_cb":
        bot.answer_callback_query(call.id); logic_view_plans(call)
    elif data == "free_host_cb":
        bot.answer_callback_query(call.id)
        call.message.from_user = call.from_user
        logic_free_host(call.message)
    elif data == "confirm_plan_upload":
        bot.answer_callback_query(call.id, "✅ Plan Verified!")
        bot.send_message(call.message.chat.id,
                         "🚀 এখন Python (.py), JS (.js) বা ZIP (.zip) ফাইল পাঠান।",
                         parse_mode="Markdown")
    elif data == "verify_join":
        joined, _ = check_force_join(user_id)
        if joined:
            bot.answer_callback_query(call.id, "✅ Welcome!")
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception: pass
            call.message.from_user = call.from_user
            send_welcome(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ সব চ্যানেলে জয়েন করুন!", show_alert=True)
    elif data == "claim_ad":
        count, activated, wait = grant_ad_reward(user_id)
        if activated:
            bot.send_message(call.message.chat.id,
                f"🎉 **অভিনন্দন!** 🎉\n━━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ **{GIGA_NEEDED}টা অ্যাড সম্পন্ন!**\n━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🤖 আপনার **{GIGA_REWARD_HOURS} ঘণ্টা ফ্রি হোস্টিং** আনলক হয়েছে!\n\n"
                f"👉 এখন **🚀 Upload File** চেপে আপনার বট হোস্ট করুন।",
                parse_mode="Markdown")
        elif wait > 0:
            bot.answer_callback_query(call.id,
                f"⏳ দয়া করে {wait} সেকেন্ড পর আবার চেষ্টা করুন।", show_alert=True)
        else:
            show_ad_verification(call.message.chat.id, user_id)

    # module installer
    elif data.startswith("instmod_"):
        _, oid, mod, fname = data.split("_", 3)
        if user_id != int(oid) and user_id not in admin_ids:
            bot.answer_callback_query(call.id, "❌ এটা আপনার ফাইল না!", show_alert=True); return
        bot.answer_callback_query(call.id)
        pkg = TELEGRAM_MODULES.get(mod.lower(), mod)
        ext = os.path.splitext(fname)[1].lower()
        st = bot.send_message(call.message.chat.id, f"⏳ Installing `{pkg}`...", parse_mode="Markdown")
        def do():
            cmd = ["npm", "install", pkg] if ext == ".js" else [sys.executable, "-m", "pip", "install", pkg]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                bot.edit_message_text(f"✅ `{pkg}` ইনস্টল হয়েছে! পুনরায় চালু হচ্ছে...",
                                      call.message.chat.id, st.message_id, parse_mode="Markdown")
                time.sleep(1)
                uf = get_user_folder(int(oid)); fp = os.path.join(uf, fname)
                run_script(fp, int(oid), uf, fname, call.message, is_js=(ext == ".js"))
            else:
                bot.edit_message_text(f"❌ ব্যর্থ!\n```\n{res.stderr[:300]}\n```",
                                      call.message.chat.id, st.message_id, parse_mode="Markdown")
        threading.Thread(target=do).start()

    elif data.startswith("viewlog_"):
        _, oid, fname = data.split("_", 2)
        rel_log = os.path.join(get_user_folder(int(oid)), f"{os.path.splitext(fname)[0]}.log")
        lp = rel_log if os.path.exists(rel_log) else \
             os.path.join(os.path.dirname(os.path.join(get_user_folder(int(oid)), fname)),
                          f"{os.path.splitext(os.path.basename(fname))[0]}.log")
        if os.path.exists(lp):
            with open(lp, "r", encoding="utf-8", errors="ignore") as f:
                logs = f.read()[-2000:]
            bot.send_message(call.message.chat.id, f"📜 **Error Log for `{fname}`:**\n\n```\n{logs or 'No logs'}\n```", parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "No log file!", show_alert=True)

    elif data.startswith("buyplan_"):
        pid = int(data.split("_")[1])
        bot.answer_callback_query(call.id)
        show_order_summary(call.message.chat.id, call.message.message_id, pid)

    # payments
    elif data.startswith("buy_bkash_"):
        pid = int(data.split("_")[2]); plan = get_plan_by_id(pid)
        if not plan: bot.answer_callback_query(call.id, "Plan not found!"); return
        bot.answer_callback_query(call.id)
        _, name, limit, price, duration, _, __ = plan
        bdt, fmt = parse_price_to_bdt(price)
        msg = (f"💚 **bKash Manual Payment**\n━━━━━━━━━━━━━━━━━━━\n"
               f"📌 **Plan:** `{name}`\n💰 **Amount:** `{bdt} BDT`\n"
               f"👤 **bKash Number:** `{get_bkash_number()}`\n🧾 **Reference:** `{PAY_REF}`\n"
               f"━━━━━━━━━━━━━━━━━━━\n\nপেমেন্ট করে TxID নিচের বাটনে জমা দিন। এডমিন যাচাই করবে।")
        mk = types.InlineKeyboardMarkup(); mk.add(ikb("📩 Submit bKash TxID", callback_data=f"bkash_txid_{pid}", style="success"))
        bot.send_message(call.message.chat.id, msg, reply_markup=mk, parse_mode="Markdown")
    elif data.startswith("bkash_txid_"):
        pid = int(data.split("_")[2]); bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "📩 আপনার **bKash TxID / Reference** লিখুন:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, lambda m: process_manual_payment(m, pid, "bKash"))
    elif data.startswith("buy_nagad_"):
        pid = int(data.split("_")[2]); plan = get_plan_by_id(pid)
        if not plan: bot.answer_callback_query(call.id, "Plan not found!"); return
        bot.answer_callback_query(call.id)
        _, name, limit, price, duration, _, __ = plan
        bdt, fmt = parse_price_to_bdt(price)
        msg = (f"🟠 **Nagad Manual Payment**\n━━━━━━━━━━━━━━━━━━━\n"
               f"📌 **Plan:** `{name}`\n💰 **Amount:** `{bdt} BDT`\n"
               f"👤 **Nagad Number:** `{get_nagad_number()}`\n🧾 **Reference:** `{PAY_REF}`\n"
               f"━━━━━━━━━━━━━━━━━━━\n\nপেমেন্ট করে TxID নিচের বাটনে জমা দিন। এডমিন যাচাই করবে।")
        mk = types.InlineKeyboardMarkup(); mk.add(ikb("📩 Submit Nagad TxID", callback_data=f"nagad_txid_{pid}", style="success"))
        bot.send_message(call.message.chat.id, msg, reply_markup=mk, parse_mode="Markdown")
    elif data.startswith("nagad_txid_"):
        pid = int(data.split("_")[2]); bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "📩 আপনার **Nagad TxID / Reference** লিখুন:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, lambda m: process_manual_payment(m, pid, "Nagad"))
    elif data.startswith("coupon_"):
        pid = int(data.split("_")[1]); bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "🎟️ আপনার **Redeem/Coupon Code** লিখুন:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, lambda m: process_coupon(m, pid))
    elif data.startswith("pay_balance_"):
        pid = int(data.split("_")[2]); bot.answer_callback_query(call.id)
        process_pay_with_balance(call.message.chat.id, user_id, pid)

    # admin settings
    elif data == "set_bkash_num" and user_id in admin_ids:
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id,
            f"💳 **নতুন bKash নাম্বার লিখুন:**\nবর্তমান: `{get_bkash_number()}`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_set_bkash)
    elif data == "set_nagad_num" and user_id in admin_ids:
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id,
            f"💳 **নতুন Nagad নাম্বার লিখুন:**\nবর্তমান: `{get_nagad_number()}`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_set_nagad)
    elif data == "set_plan_banner" and user_id in admin_ids:
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id,
            "🖼️ **প্ল্যান ব্যানার ছবিটি পাঠান** (Buy Plan-এ প্রথমে এটাই দেখানো হবে):", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_set_banner)
    elif data == "set_orders_group" and user_id in admin_ids:
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id,
            "👥 **অর্ডার গ্রুপ সেট করতে:**\n"
            "১. বটকে ওই গ্রুপে **এডমিন** হিসেবে যোগ করুন।\n"
            "২. এবার সেই গ্রুপে গিয়ে সরাসরি লিখুন:\n`/setordergroup`\n\n"
            "*(ফরওয়ার্ড করে কাজ হয় না — গ্রুপে গিয়ে কমান্ডটা পাঠাতে হবে।)*",
            parse_mode="Markdown")
    elif data == "set_ref_reward" and user_id in admin_ids:
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id,
            f"🎯 **প্রতি রেফারে কত টাকা দেবেন তা লিখুন (শুধু সংখ্যা):**\nবর্তমান: `{get_referral_reward()} BDT`",
            parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_set_ref_reward)
    elif data == "set_support_link" and user_id in admin_ids:
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id,
            f"💬 **নতুন Support লিংক দিন (t.me/... )**:\nবর্তমান: `{get_support_link()}`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_set_support_link)
    elif data == "set_update_channel" and user_id in admin_ids:
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id,
            f"📢 **নতুন Update Channel লিংক দিন:**\nবর্তমান: `{get_update_channel()}`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_set_update_channel)
    elif data == "gen_redeem_code" and user_id in admin_ids:
        bot.answer_callback_query(call.id)
        plans = get_all_plans()
        if not plans:
            bot.send_message(call.message.chat.id, "ℹ️ প্রথমে একটা প্ল্যান যোগ করুন।"); return
        mk = types.InlineKeyboardMarkup(row_width=1)
        for p in plans:
            pid, name, limit, price, duration, buy_link, features = p
            mk.add(ikb(f"{plan_icon(name)} {name}", callback_data=f"genc_{pid}", style="primary"))
        bot.send_message(call.message.chat.id, "🎟️ **কোন প্ল্যানের জন্য কোড বানাবেন?**", reply_markup=mk, parse_mode="Markdown")
    elif data.startswith("genc_") and user_id in admin_ids:
        pid = int(data.split("_")[1])
        plan = get_plan_by_id(pid)
        if not plan:
            bot.answer_callback_query(call.id, "Plan not found!"); return
        bot.answer_callback_query(call.id)
        code = generate_redeem_code(pid)
        bot.send_message(call.message.chat.id,
            f"✅ **নতুন কোড তৈরি হয়েছে!**\n📦 Plan: `{plan[1]}`\n🎟️ Code: `{code}`\n\n"
            f"এই কোডটা ইউজারকে দিন — সে **Buy Plan → 🎟️ Redeem Code**-এ গিয়ে দিলেই প্ল্যান এক্টিভ হয়ে যাবে।",
            parse_mode="Markdown")
    elif data == "lang_bn":
        bot.answer_callback_query(call.id)
        set_user_lang(user_id, "bn")
        bot.send_message(call.message.chat.id, t(user_id, "lang_set"),
                         reply_markup=create_main_menu(user_id), parse_mode="Markdown")
    elif data == "lang_en":
        bot.answer_callback_query(call.id)
        set_user_lang(user_id, "en")
        bot.send_message(call.message.chat.id, t(user_id, "lang_set"),
                         reply_markup=create_main_menu(user_id), parse_mode="Markdown")
    elif data == "onboard_lang_bn":
        bot.answer_callback_query(call.id)
        set_user_lang(user_id, "bn")
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception: pass
        call.message.from_user = call.from_user
        send_welcome(call.message)
    elif data == "onboard_lang_en":
        bot.answer_callback_query(call.id)
        set_user_lang(user_id, "en")
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception: pass
        call.message.from_user = call.from_user
        send_welcome(call.message)

    # admin
    elif data == "add_plan_init" and user_id in admin_ids:
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id,
            "📝 **Plan details (format):**\n`Name | FileLimit | Price | Days | BuyLink | Features`\n\n"
            "Features গুলো `•` দিয়ে আলাদা করুন।\n\n"
            "*Ex:* `Pro | 1 | 30 | 7 | https://t.me/owner | 24/7 Uptime • Ad-Free • 1 Bot • Auto-Renew`",
            parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_add_plan)
    elif data == "manage_plans" and user_id in admin_ids:
        bot.answer_callback_query(call.id); plans = get_all_plans()
        if not plans: bot.send_message(call.message.chat.id, "No plans."); return
        mk = types.InlineKeyboardMarkup()
        for p in plans: mk.add(ikb(f"🗑️ {p[1]}", callback_data=f"del_plan_{p[0]}", style="danger"))
        bot.send_message(call.message.chat.id, "🗑️ Select plan to delete:", reply_markup=mk)
    elif data.startswith("del_plan_") and user_id in admin_ids:
        delete_plan_db(int(data.split("_")[2])); bot.answer_callback_query(call.id, "Deleted!")
        bot.send_message(call.message.chat.id, "✅ Deleted.")
    elif data == "add_subscription" and user_id in admin_ids:
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "💎 **Format:** `UserID PlanName Days`\n*Ex:* `123456789 VIP 30`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_add_sub)
    elif data == "remove_subscription" and user_id in admin_ids:
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "❌ **User ID দিন (subscription remove করতে):**", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_remove_sub)
    elif data == "broadcast" and user_id in admin_ids:
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id,
            "📣 **যা ব্রডকাস্ট করতে চান পাঠান** (টেক্সট, ছবি, ভিডিও — যেকোনো কিছু):", parse_mode="Markdown")
        bot.register_next_step_handler(msg, broadcast_message)
    elif data == "toggle_lock" and user_id in admin_ids:
        global bot_locked
        bot_locked = not bot_locked; bot.answer_callback_query(call.id, f"Locked: {bot_locked}")
        bot.send_message(call.message.chat.id, f"🔐 Bot now: `{'Locked' if bot_locked else 'Unlocked'}`", parse_mode="Markdown")
    elif data == "force_join_menu" and user_id in admin_ids:
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📢 **Force Join Channels:**", reply_markup=force_join_menu())
    elif data == "addfjoin" and user_id in admin_ids:
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id,
            "🔗 **Channel-এর জয়েন লিংক পাঠান** (public হলে `https://t.me/username`, "
            "প্রাইভেট হলে invite link `https://t.me/+xxxx`):", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_add_fjoin)
    elif data.startswith("rmfjoin_") and user_id in admin_ids:
        remove_force_join_channel(int(data.split("_")[1])); bot.answer_callback_query(call.id, "Removed!")
        bot.send_message(call.message.chat.id, "📢 **Force Join Channels:**", reply_markup=force_join_menu())
    elif data == "back_admin" and user_id in admin_ids:
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🛡️ **Admin Panel:**", reply_markup=admin_panel_inline(), parse_mode="Markdown")
    elif data == "stats" and user_id in admin_ids:
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id,
            f"📊 Active Users: `{len(active_users)}`\n👥 Uploaders: `{len(user_files)}`\n🤖 Running Scripts: `{len(bot_scripts)}`",
            parse_mode="Markdown")

    # file management (🎨 colored)
    elif data.startswith("file_"):
        _, oid, fname = data.split("_", 2)
        running = is_bot_running(int(oid), fname)
        mk = types.InlineKeyboardMarkup(row_width=2)
        if running:
            mk.add(ikb("🔴 Stop", callback_data=f"stop_{oid}_{fname}", style="danger"))
        else:
            mk.add(ikb("🟢 Start", callback_data=f"start_{oid}_{fname}", style="success"))
        mk.add(ikb("🗑️ Delete", callback_data=f"del_{oid}_{fname}", style="danger"))
        bot.send_message(call.message.chat.id, f"📄 File: `{fname}`\n🚦 Status: `{'Running' if running else 'Stopped'}`", reply_markup=mk, parse_mode="Markdown")
    elif data.startswith("stop_"):
        _, oid, fname = data.split("_", 2); skey = f"{oid}_{fname}"
        if skey in bot_scripts: kill_process_tree(bot_scripts.pop(skey, {}))
        bot.answer_callback_query(call.id, "Stopped!"); bot.send_message(call.message.chat.id, f"🛑 `{fname}` stopped.", parse_mode="Markdown")
    elif data.startswith("start_"):
        _, oid, fname = data.split("_", 2)
        uf = get_user_folder(int(oid)); fp = os.path.join(uf, fname)
        ext = os.path.splitext(fname)[1].lower()
        bot.answer_callback_query(call.id, "Starting!")
        run_script(fp, int(oid), uf, fname, call.message, is_js=(ext == ".js"))
    elif data.startswith("del_"):
        _, oid, fname = data.split("_", 2); skey = f"{oid}_{fname}"
        if skey in bot_scripts: kill_process_tree(bot_scripts.pop(skey, {}))
        remove_user_file_db(int(oid), fname)
        fp = os.path.join(get_user_folder(int(oid)), fname)
        if os.path.exists(fp): os.remove(fp)
        bot.answer_callback_query(call.id, "Deleted!"); bot.send_message(call.message.chat.id, f"🗑️ `{fname}` deleted.", parse_mode="Markdown")

# =====================================================================
#  STEP HANDLERS
# =====================================================================
def process_manual_payment(message, plan_id, method):
    txid = message.text.strip(); user_id = message.from_user.id
    plan = get_plan_by_id(plan_id)
    if not plan: bot.reply_to(message, "❌ Plan not found!"); return
    _, name, limit, price, duration, _, __ = plan
    bdt, fmt = parse_price_to_bdt(price)
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO pending_payments (user_id, plan_id, method, txid) "
                  "VALUES (?, ?, ?, ?)", (user_id, plan_id, method, txid))
        conn.commit(); conn.close()
    msg = bot.reply_to(message,
        f"📩 **TxID রেকর্ড হয়েছে!**\n\n💎 Plan: `{name}`\n💰 Amount: `{bdt} BDT`\n🧾 TxID: `{txid}`\n\n"
        f"📸 **এবার পেমেন্টের স্ক্রিনশটটি পাঠান** (ছবি হিসেবে):",
        parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: process_payment_screenshot(m, plan_id, method, txid))

def process_payment_screenshot(message, plan_id, method, txid):
    user_id = message.from_user.id
    if not message.photo:
        msg = bot.reply_to(message, "❌ এটা ছবি না। অনুগ্রহ করে পেমেন্টের **স্ক্রিনশট (ছবি)** পাঠান:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, lambda m: process_payment_screenshot(m, plan_id, method, txid))
        return
    plan = get_plan_by_id(plan_id)
    name = plan[1] if plan else "?"
    bdt, fmt = parse_price_to_bdt(plan[3]) if plan else ("?", "?")
    uname = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    caption = (f"🧾 **নতুন অর্ডার**\n━━━━━━━━━━━━━━━━━━━\n"
               f"👤 User: `{user_id}` ({uname})\n💎 Plan: `{name}`\n"
               f"💰 Amount: `{bdt} BDT`\n💳 Method: `{method}`\n🧾 TxID: `{txid}`\n"
               f"━━━━━━━━━━━━━━━━━━━\n⏳ যাচাই করে `Add Subscription` দিয়ে এক্টিভ করুন।")
    photo_id = message.photo[-1].file_id
    target = get_orders_group() or OWNER_ID
    try:
        bot.send_photo(target, photo_id, caption=caption, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Order forward failed: {e}")
        try:
            bot.send_photo(OWNER_ID, photo_id, caption=caption, parse_mode="Markdown")
        except Exception:
            pass
    bot.reply_to(message,
        "✅ **আপনার অর্ডার জমা হয়েছে!**\nএডমিন যাচাই করে শীঘ্রই আপনার প্ল্যান এক্টিভ করে দেবেন। 🙏",
        parse_mode="Markdown")

def process_add_plan(message):
    try:
        parts = [p.strip() for p in message.text.split("|")]
        name, limit, price, duration, buy_link = parts[0], int(parts[1]), parts[2], int(parts[3]), parts[4]
        features = parts[5] if len(parts) > 5 else ""
        add_plan_db(name, limit, price, duration, buy_link, features)
        bot.reply_to(message, f"✅ Plan `{name}` added!", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Invalid format: {e}")

def process_add_sub(message):
    try:
        parts = message.text.split()
        uid, pname, days = int(parts[0]), parts[1], int(parts[2])
        activate_user_plan(uid, pname, days)
        bot.reply_to(message, f"✅ Sub active for `{uid}` ({pname}, {days}d) — ইউজারকে নোটিফিকেশন পাঠানো হয়েছে।", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

def process_remove_sub(message):
    try:
        uid = int(message.text.strip()); remove_subscription_db(uid)
        bot.reply_to(message, f"✅ Sub removed for `{uid}`", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

def process_coupon(message, plan_id):
    code = message.text.strip().upper()
    user_id = message.from_user.id
    plan = get_plan_by_id(plan_id)
    if not plan:
        bot.reply_to(message, "❌ Plan not found!"); return
    _, name, limit, price, duration, _, __ = plan
    bdt, fmt = parse_price_to_bdt(price)

    redeemed_plan = redeem_code_use(code, user_id)
    if redeemed_plan:
        rp_name, rp_duration = redeemed_plan
        activate_user_plan(user_id, rp_name, rp_duration)
        bot.reply_to(message,
            f"🎉 **কোড রিডিম সফল হয়েছে!**\n✨ **{rp_name}** প্ল্যান এখনই এক্টিভ হয়ে গেছে — উপরে দেখুন!",
            parse_mode="Markdown")
        return

    discount = COUPONS.get(code)
    if discount:
        new_amt = int(int(bdt) * (100 - discount) / 100)
        bot.reply_to(message,
            f"🎉 **কুপন প্রয়োগ হয়েছে!**\n📌 Plan: `{name}`\n"
            f"💰 আগের দাম: `{bdt} BDT` ➜ নতুন দাম: `{new_amt} BDT` (`-{discount}%`)\n\n"
            f"👉 এবার পেমেন্ট মেথড বেছে নিয়ে সম্পূর্ণ করুন।",
            parse_mode="Markdown")
        return

    bot.reply_to(message, "❌ **কোডটি সঠিক নয়, মেয়াদ শেষ, অথবা আগেই ব্যবহার হয়ে গেছে।**", parse_mode="Markdown")

def process_pay_with_balance(chat_id, user_id, plan_id):
    plan = get_plan_by_id(plan_id)
    if not plan:
        bot.send_message(chat_id, "❌ Plan not found!"); return
    _, name, limit, price, duration, _, __ = plan
    bdt, fmt = parse_price_to_bdt(price)
    acc = get_account(user_id)
    if acc["balance"] < float(bdt):
        bot.send_message(chat_id,
            f"❌ **ব্যালেন্স যথেষ্ট নয়!**\n💰 আপনার ব্যালেন্স: `{round(acc['balance'],2)} BDT`\n"
            f"💳 প্রয়োজন: `{bdt} BDT`\n\n👥 বন্ধুদের রেফার করে আরও ব্যালেন্স আয় করুন — 👤 Account দেখুন।",
            parse_mode="Markdown")
        return
    deduct_balance(user_id, float(bdt))
    activate_user_plan(user_id, name, duration)
    bot.send_message(chat_id,
        f"✅ **ব্যালেন্স থেকে পেমেন্ট সম্পন্ন হয়েছে!**\n💳 কেটে নেওয়া হলো: `{bdt} BDT`\n"
        f"✨ **{name}** প্ল্যান এখনই এক্টিভ!", parse_mode="Markdown")

def process_add_fjoin(message):
    link = message.text.strip()
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT INTO force_join (link, chat_ref) VALUES (?, NULL)", (link,))
        rowid = c.lastrowid
        conn.commit(); conn.close()

    username = extract_username(link)
    if username:
        try:
            chat = bot.get_chat(username)
            set_force_join_ref(rowid, str(chat.id))
            bot.reply_to(message, f"✅ Channel added ও ভেরিফাই রেডি: `{link}`", parse_mode="Markdown")
            bot.send_message(message.chat.id, "📢 **Force Join Channels:**", reply_markup=force_join_menu())
            return
        except Exception:
            pass

    msg = bot.reply_to(message,
        f"✅ Channel added: `{link}`\n\n"
        f"⚠️ **আরেকটা ধাপ বাকি (জরুরি!):** এই চ্যানেলের যেকোনো একটা পোস্ট এখানে **ফরওয়ার্ড** করুন — "
        f"তাহলেই বট সঠিকভাবে মেম্বারশিপ চেক করতে পারবে।",
        parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: process_fjoin_ref(m, rowid))

def process_fjoin_ref(message, rowid):
    chat = message.forward_from_chat
    if not chat:
        msg = bot.reply_to(message,
            "❌ এটা কোনো চ্যানেলের ফরওয়ার্ড করা পোস্ট না। ওই চ্যানেলের একটা পোস্ট এখানে ফরওয়ার্ড করুন:",
            parse_mode="Markdown")
        bot.register_next_step_handler(msg, lambda m: process_fjoin_ref(m, rowid))
        return
    set_force_join_ref(rowid, str(chat.id))
    bot.reply_to(message, f"✅ **{chat.title}** verify-রেডি হয়ে গেছে!", parse_mode="Markdown")
    bot.send_message(message.chat.id, "📢 **Force Join Channels:**", reply_markup=force_join_menu())

def process_set_bkash(message):
    num = message.text.strip()
    set_setting("bkash_number", num)
    bot.reply_to(message, f"✅ bKash নাম্বার সেট হয়েছে: `{num}`", parse_mode="Markdown")

def process_set_nagad(message):
    num = message.text.strip()
    set_setting("nagad_number", num)
    bot.reply_to(message, f"✅ Nagad নাম্বার সেট হয়েছে: `{num}`", parse_mode="Markdown")

def process_set_banner(message):
    if not message.photo:
        msg = bot.reply_to(message, "❌ এটা ছবি না। অনুগ্রহ করে একটা **ছবি** পাঠান:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_set_banner)
        return
    set_setting("plan_banner_file_id", message.photo[-1].file_id)
    bot.reply_to(message, "✅ প্ল্যান ব্যানার সেট হয়েছে!", parse_mode="Markdown")

def process_set_ref_reward(message):
    try:
        amt = float(message.text.strip())
        set_setting("referral_reward", amt)
        bot.reply_to(message, f"✅ রেফার রিওয়ার্ড সেট হয়েছে: `{amt} BDT` প্রতি রেফারে", parse_mode="Markdown")
    except ValueError:
        bot.reply_to(message, "❌ শুধু সংখ্যা লিখুন (যেমন: 5 বা 10.5)।")

def process_set_support_link(message):
    link = message.text.strip()
    set_setting("support_link", link)
    bot.reply_to(message, f"✅ Support লিংক সেট হয়েছে: `{link}`", parse_mode="Markdown")

def process_set_update_channel(message):
    link = message.text.strip()
    set_setting("update_channel", link)
    bot.reply_to(message, f"✅ Update Channel লিংক সেট হয়েছে: `{link}`", parse_mode="Markdown")

def broadcast_message(message):
    sent, failed = 0, 0
    targets = set(active_users) | set(user_subscriptions.keys())
    for uid in targets:
        try:
            bot.copy_message(uid, message.chat.id, message.message_id)
            sent += 1
        except Exception:
            failed += 1
        time.sleep(0.05)
    bot.reply_to(message, f"📣 **Broadcast সম্পন্ন!**\n✅ Sent: `{sent}`\n❌ Failed: `{failed}`", parse_mode="Markdown")

# =====================================================================
#  TEXT BUTTON MAPPING
# =====================================================================
def logic_admin_panel(message):
    if message.from_user.id not in admin_ids:
        return
    bot.reply_to(message, "🛡️ **Admin Panel:**",
                 reply_markup=admin_panel_inline(), parse_mode="Markdown")

def logic_bot_stats(message):
    bot.reply_to(message,
        f"📊 Active Users: `{len(active_users)}`\n🤖 Running Scripts: `{len(bot_scripts)}`",
        parse_mode="Markdown")

# key -> handler (ভাষা যাই হোক, কাজ একটাই)
BUTTON_HANDLERS = {
    "free_host": logic_free_host,
    "buy_plan":  logic_view_plans,
    "upload":    logic_upload,
    "manage":    logic_check_files,
    "support":   logic_support,
    "updates":   logic_updates,
    "account":   logic_account,
    "language":  logic_language,
    "speed":     logic_speed,
    "stats":     logic_bot_stats,
    "admin":     logic_admin_panel,
}

# দুই ভাষার সব লেবেল একই হ্যান্ডলারে ম্যাপ করা — বাংলা/English যেই বাটনই চাপুক কাজ করবে
BUTTON_MAPPING = {}
for _key, _func in BUTTON_HANDLERS.items():
    for _lang in ("bn", "en"):
        BUTTON_MAPPING[MENU_BUTTON_LABELS[_key][_lang]] = _func
# পুরনো ভার্সনের কিবোর্ড ক্যাশে থাকলে যেন তাও কাজ করে
BUTTON_MAPPING["🚀 𝗨𝗽𝗹𝗼𝗮d 𝗙𝗶𝗹𝗲"] = logic_upload

@bot.message_handler(func=lambda m: m.text in BUTTON_MAPPING)
def handle_buttons(message):
    BUTTON_MAPPING[message.text](message)

@bot.message_handler(commands=["setordergroup"])
def set_order_group_cmd(message):
    if message.from_user.id not in admin_ids:
        return
    if message.chat.type not in ("group", "supergroup"):
        bot.reply_to(message, "❌ এই কমান্ডটা গ্রুপের ভেতরে গিয়ে পাঠাতে হবে।")
        return
    set_setting("orders_group_id", message.chat.id)
    bot.reply_to(message, f"✅ এই গ্রুপ ({message.chat.title}) এখন থেকে অর্ডার গ্রুপ হিসেবে সেট হলো!")

@bot.message_handler(commands=["start"])
def start_cmd(message):
    user_id = message.from_user.id
    ensure_account(user_id)
    if " " in message.text:
        parts = message.text.split()
        if len(parts) > 1 and parts[1] == "claim_ad":
            count, activated, wait = grant_ad_reward(user_id)
            if activated:
                bot.send_message(message.chat.id,
                    f"🎉 **অভিনন্দন!** 🎉\n━━━━━━━━━━━━━━━━━━━━━\n"
                    f"✅ **{GIGA_NEEDED}টা অ্যাড সম্পন্ন!**\n━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🤖 আপনার **{GIGA_REWARD_HOURS} ঘণ্টা ফ্রি হোস্টিং** আনলক হয়েছে!\n\n"
                    f"👉 এখন **🚀 Upload File** চেপে আপনার বট হোস্ট করুন।",
                    parse_mode="Markdown")
            elif wait > 0:
                bot.send_message(message.chat.id,
                    f"⏳ **অনুগ্রহ করে {wait} সেকেন্ড পর আবার চেষ্টা করুন।**\n"
                    f"অ্যাডটি শেষ পর্যন্ত দেখে ফিরে আসুন।", parse_mode="Markdown")
            else:
                show_ad_verification(message.chat.id, user_id)
            return
        if len(parts) > 1 and parts[1].startswith("ref_"):
            try:
                referrer_id = int(parts[1].split("ref_")[1])
                if register_referral(referrer_id, user_id):
                    try:
                        bot.send_message(referrer_id,
                            f"🎉 আপনার রেফার লিংক দিয়ে একজন নতুন ইউজার যোগ দিয়েছে!\n"
                            f"💰 আপনার ব্যালেন্সে `{get_referral_reward()} BDT` যোগ হয়েছে।",
                            parse_mode="Markdown")
                    except Exception:
                        pass
            except (ValueError, IndexError):
                pass
    send_welcome(message)

# =====================================================================
#  CLEANUP & START
# =====================================================================
def cleanup():
    for key in list(bot_scripts.keys()):
        kill_process_tree(bot_scripts[key])

atexit.register(cleanup)

if __name__ == "__main__":
    logger.info("🤖 Starting Premium Host Bot (Colored Buttons + bKash/Nagad + Force Join)...")
    if BTN_STYLE_SUPPORTED:
        logger.info("🎨 Colored buttons: ENABLED (Bot API 9.4)")
    else:
        logger.warning("🎨 Colored buttons: DISABLED — run: pip install -U pyTelegramBotAPI")
    keep_alive()
    bot.infinity_polling(timeout=60, long_polling_timeout=30)
