import os
import json
import time
import requests
from datetime import datetime
from typing import Dict, List

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

MAX_RETRIES = 3
REQUEST_TIMEOUT = 10

# ============ MANAJEMEN DATA ============
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
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            return get_default_data()
    else:
        return get_default_data()

    # default key
    data.setdefault("rules", DEFAULT_RULES)
    data.setdefault("label", DEFAULT_LABEL)
    data.setdefault("price", DEFAULT_PRICE)
    data.setdefault("global_slot", DEFAULT_SLOT)
    data.setdefault("job_active", True)
    data.setdefault("users", {})

    # migrate user
    for uid, u in data["users"].items():
        u.setdefault("slot", data["global_slot"])
        u.setdefault("accounts", [])
        u.setdefault("total", len(u["accounts"]))
        u.setdefault("dana", "")

    return data

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

data = load_data()

# ============ CEK FACEBOOK ============
def check_facebook_live(uid: str) -> Dict:
    url = f"https://www.facebook.com/{uid}"

    for _ in range(MAX_RETRIES):
        try:
            r = requests.get(url, timeout=REQUEST_TIMEOUT)
            txt = r.text.lower()

            if r.status_code == 200:
                if "checkpoint" in txt:
                    return {"status": "⚠️ CHECKPOINT", "emoji": "⚠️", "live": False}
                elif "not found" in txt:
                    return {"status": "❌ TIDAK DITEMUKAN", "emoji": "❌", "live": False}
                else:
                    return {"status": "✅ LIVE", "emoji": "✅", "live": True}
            elif r.status_code == 404:
                return {"status": "❌ TIDAK DITEMUKAN", "emoji": "❌", "live": False}

        except:
            time.sleep(1)

    return {"status": "⚠️ ERROR", "emoji": "⚠️", "live": False}

# ============ HELPER ============
def get_user_slot(uid):
    return data["users"].get(uid, {}).get("slot", data["global_slot"])

def get_remaining(uid):
    used = len(data["users"].get(uid, {}).get("accounts", []))
    return max(0, get_user_slot(uid) - used)

# ============ HANDLER ============
def start(update: Update, context: CallbackContext):
    uid = str(update.effective_user.id)
    name = update.effective_user.first_name

    if uid not in data["users"]:
        data["users"][uid] = {"dana": "", "total": 0, "accounts": [], "slot": data["global_slot"]}
        save_data(data)

    user = data["users"][uid]

    text = f"""Halo {name}

Total: {user['total']}
Slot: {get_user_slot(uid)}
Sisa: {get_remaining(uid)}

Harga: Rp {data['price']:,}
Label: {data['label']}

Gunakan:
/setdana
/ceklive
/live
"""

    update.message.reply_text(text)

def set_dana(update: Update, context: CallbackContext):
    uid = str(update.effective_user.id)

    if not context.args:
        update.message.reply_text("Format: /setdana 08xxx")
        return

    nomor = context.args[0]

    data["users"].setdefault(uid, {"dana": "", "total": 0, "accounts": [], "slot": data["global_slot"]})
    data["users"][uid]["dana"] = nomor
    save_data(data)

    update.message.reply_text("✅ Dana disimpan")

def handle_account(update: Update, context: CallbackContext):
    uid = str(update.effective_user.id)

    if uid not in data["users"] or not data["users"][uid]["dana"]:
        update.message.reply_text("Set dana dulu")
        return

    lines = update.message.text.split("\n")
    uids = [x.strip() for x in lines if x.strip().isdigit()]

    if not uids:
        return

    if len(uids) > get_remaining(uid):
        update.message.reply_text("Slot tidak cukup")
        return

    msg = "Hasil:\n"

    for u in uids:
        res = check_facebook_live(u)

        data["users"][uid]["accounts"].append({
            "uid": u,
            "status": res["status"],
            "time": datetime.now().isoformat()
        })

        data["users"][uid]["total"] += 1
        msg += f"{res['emoji']} {u}\n"

        time.sleep(0.2)

    save_data(data)
    update.message.reply_text(msg)

# ============ MAIN ============
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setdana", set_dana))
    app.add_handler(CommandHandler("ceklive", cek_live_command))
    app.add_handler(CommandHandler("live", live_command))
    
    app.add_handler(CommandHandler("rules", rules_command))
    app.add_handler(CommandHandler("setjob", set_job))
    app.add_handler(CommandHandler("setrules", set_rules))
    app.add_handler(CommandHandler("setlabel", set_label))
    app.add_handler(CommandHandler("setharga", set_price))
    app.add_handler(CommandHandler("setslot", set_slot_user))
    app.add_handler(CommandHandler("setglobalslot", set_global_slot))
    app.add_handler(CommandHandler("total", total_user))
    app.add_handler(CommandHandler("bayar", payout))
    app.add_handler(CommandHandler("semuauser", all_users))
    
    # Handle text
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_account))
    
    print(f"✅ Bot started!")
    print(f"📱 Owner ID: {OWNER_ID}")
    print(f"🌍 Global slot: {data.get('global_slot', DEFAULT_SLOT)}")
    print(f"💰 Harga: Rp {data.get('price', DEFAULT_PRICE):,}")
    
    app.run_polling()

if __name__ == "__main__":
    main()
