import os
import json
import time
import requests
from datetime import datetime

from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# ================= CONFIG =================
TOKEN = os.getenv("TOKEN")
OWNER_ID = 5312657021
DATA_FILE = "data.json"

DEFAULT_RULES = "Tidak boleh spam, akun harus valid"
DEFAULT_PRICE = 300
DEFAULT_LABEL = "FB"
DEFAULT_SLOT = 50

# ================= DATA =================
def get_default_data():
    return {
        "users": {},
        "job_active": True,
        "rules": DEFAULT_RULES,
        "price": DEFAULT_PRICE,
        "label": DEFAULT_LABEL,
        "global_slot": DEFAULT_SLOT
    }

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)

                data.setdefault("users", {})
                data.setdefault("rules", DEFAULT_RULES)
                data.setdefault("price", DEFAULT_PRICE)
                data.setdefault("label", DEFAULT_LABEL)
                data.setdefault("global_slot", DEFAULT_SLOT)
                data.setdefault("job_active", True)

                for uid, u in data["users"].items():
                    u.setdefault("slot", data["global_slot"])
                    u.setdefault("accounts", [])
                    u.setdefault("total", len(u["accounts"]))
                    u.setdefault("dana", "")

                return data
        except:
            return get_default_data()
    return get_default_data()

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# ================= FB CHECK =================
def check_facebook_live(uid):
    try:
        res = requests.get(
            f"https://www.facebook.com/{uid}",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        text = res.text.lower()

        if "checkpoint" in text:
            return {"status": "⚠️ CHECKPOINT", "emoji": "⚠️", "live": False}
        if "not found" in text or res.status_code == 404:
            return {"status": "❌ NOT FOUND", "emoji": "❌", "live": False}

        return {"status": "✅ LIVE", "emoji": "✅", "live": True}
    except:
        return {"status": "⚠️ ERROR", "emoji": "⚠️", "live": False}

# ================= SLOT =================
def get_user_slot(uid):
    return data["users"].get(uid, {}).get("slot", data["global_slot"])

def get_remaining_slot(uid):
    used = len(data["users"].get(uid, {}).get("accounts", []))
    return max(0, get_user_slot(uid) - used)

# ================= COMMAND =================
def start(update: Update, context: CallbackContext):
    uid = str(update.effective_user.id)

    if uid not in data["users"]:
        data["users"][uid] = {"dana": "", "total": 0, "accounts": [], "slot": data["global_slot"]}
        save_data(data)

    u = data["users"][uid]

    text = f"""👋 Halo!

📊 Akun kamu:
Total: {u['total']}
Slot: {len(u['accounts'])}/{get_user_slot(uid)}
Sisa: {get_remaining_slot(uid)}

💰 Harga: Rp {data['price']:,}

Menu:
/setdana 08xxxx
/ceklive
/live
"""
    update.message.reply_text(text)

def set_dana(update: Update, context: CallbackContext):
    uid = str(update.effective_user.id)

    if not context.args:
        return update.message.reply_text("Format: /setdana 08xxx")

    data["users"][uid]["dana"] = context.args[0]
    save_data(data)

    update.message.reply_text("✅ DANA tersimpan")

def ceklive(update: Update, context: CallbackContext):
    update.message.reply_text("Kirim UID (1 baris 1)")
    context.user_data["cek"] = True

def handle_text(update: Update, context: CallbackContext):
    uid = str(update.effective_user.id)
    text = update.message.text.strip()

    # MODE CEK
    if context.user_data.get("cek"):
        context.user_data["cek"] = False
        uids = text.splitlines()

        hasil = ""
        for u in uids:
            r = check_facebook_live(u)
            hasil += f"{r['emoji']} {u}: {r['status']}\n"

        return update.message.reply_text(hasil)

    # SETOR
    if not data["job_active"]:
        return update.message.reply_text("⛔ Job tutup")

    if not data["users"][uid]["dana"]:
        return update.message.reply_text("Set /setdana dulu")

    uids = [x for x in text.splitlines() if x.isdigit()]

    if not uids:
        return

    if len(uids) > get_remaining_slot(uid):
        return update.message.reply_text("Slot tidak cukup")

    hasil = ""
    for u in uids:
        r = check_facebook_live(u)

        data["users"][uid]["accounts"].append({
            "uid": u,
            "status": r["status"],
            "time": datetime.now().isoformat()
        })
        data["users"][uid]["total"] += 1

        hasil += f"{r['emoji']} {u}: {r['status']}\n"

        time.sleep(0.2)

    save_data(data)
    update.message.reply_text(hasil)

def live(update: Update, context: CallbackContext):
    uid = str(update.effective_user.id)

    user = data["users"][uid]
    if not user["accounts"]:
        return update.message.reply_text("Kosong")

    text = ""
    for i, a in enumerate(user["accounts"], 1):
        text += f"{i}. {a['uid']} - {a['status']}\n"

    update.message.reply_text(text[:4000])

# ================= ADMIN =================
def setjob(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID:
        return

    if not context.args:
        return update.message.reply_text("/setjob open/close")

    data["job_active"] = context.args[0] == "open"
    save_data(data)

    update.message.reply_text("Updated")

# ================= RUN =================
updater = Updater(TOKEN, use_context=True)
dp = updater.dispatcher

dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("setdana", set_dana))
dp.add_handler(CommandHandler("ceklive", ceklive))
dp.add_handler(CommandHandler("live", live))
dp.add_handler(CommandHandler("setjob", setjob))

dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

print("BOT RUNNING...")
updater.start_polling()
updater.idle()
