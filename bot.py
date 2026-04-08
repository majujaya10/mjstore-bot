import os
import re
import pandas as pd
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ================= CONFIG =================
import os

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN belum diset di Railway Variables!")
ADMIN_ID = 5312657021
FILE = "data.json"

# ================= INIT EXCEL =================
def init_file():
    try:
        pd.read_excel(FILE)
    except:
        df = pd.DataFrame(columns=["user_id", "username", "dana", "uid", "waktu"])
        df.to_excel(FILE, index=False)

init_file()

user_dana = {}

# ================= FUNCTION =================
def extract_uid(text):
    match = re.search(r'c_user=(\d+)', text)
    return match.group(1) if match else None

def save_data(user_id, username, dana, uid):
    df = pd.read_excel(FILE)

    if uid in df["uid"].astype(str).values:
        return False

    new = {
        "user_id": user_id,
        "username": username or "-",
        "dana": dana,
        "uid": uid,
        "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
    df.to_excel(FILE, index=False)
    return True

# ================= COMMAND =================
async def set_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Hanya admin!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ /setjob open | /setjob close")
        return
    
    action = context.args[0].lower()
    if action == "open":
        data["job_active"] = True
        save_data(data)
        await update.message.reply_text("✅ JOB DIBUKA!")
    elif action == "close":
        data["job_active"] = False
        save_data(data)
        await update.message.reply_text("⛔ JOB DITUTUP!")
    else:
        await update.message.reply_text("❌ Pilihan: open atau close")

async def set_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Hanya admin!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ /setrules <teks rules>")
        return
    
    data["rules"] = " ".join(context.args)
    save_data(data)
    await update.message.reply_text(f"✅ Rules diupdate!\n\n{data['rules']}")

async def set_label(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Hanya admin!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ /setlabel <label>")
        return
    
    data["label"] = " ".join(context.args)
    save_data(data)
    await update.message.reply_text(f"✅ Label diubah menjadi: {data['label']}")

async def set_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Hanya admin!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ /setharga <harga>")
        return
    
    try:
        new_price = int(context.args[0])
        data["price"] = new_price
        save_data(data)
        await update.message.reply_text(f"✅ Harga per akun: Rp {new_price:,}")
    except:
        await update.message.reply_text("❌ Masukkan angka!")

async def set_slot_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Hanya admin!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("❌ /setslot <UID_user> <slot>")
        return
    
    target_uid = context.args[0]
    try:
        new_slot = int(context.args[1])
    except:
        await update.message.reply_text("❌ Slot harus angka!")
        return
    
    if target_uid not in data["users"]:
        data["users"][target_uid] = {"dana": "", "total": 0, "accounts": [], "slot": new_slot}
    else:
        data["users"][target_uid]["slot"] = new_slot
    
    save_data(data)
    await update.message.reply_text(f"✅ Slot user {target_uid} = {new_slot}")

async def set_global_slot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Hanya admin!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ /setglobalslot <slot>")
        return
    
    try:
        new_slot = int(context.args[0])
        data["global_slot"] = new_slot
        save_data(data)
        await update.message.reply_text(f"✅ Global slot: {new_slot}")
    except:
        await update.message.reply_text("❌ Masukkan angka!")

async def total_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Hanya admin!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ /total <UID>")
        return
    
    target = context.args[0]
    if target in data["users"]:
        u = data["users"][target]
        await update.message.reply_text(f"UID: {target}\nDANA: {u['dana']}\nTotal: {u['total']} akun\nNominal: Rp {u['total'] * data.get('price', DEFAULT_PRICE):,}")
    else:
        await update.message.reply_text("User tidak ditemukan")

async def payout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Hanya admin!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("❌ /bayar <UID> <jumlah>")
        return
    
    target = context.args[0]
    try:
        jumlah = int(context.args[1])
    except:
        await update.message.reply_text("❌ Jumlah harus angka!")
        return
    
    if target not in data["users"]:
        await update.message.reply_text("User tidak ditemukan")
        return
    
    if data["users"][target]["total"] < jumlah:
        await update.message.reply_text(f"User hanya punya {data['users'][target]['total']} akun")
        return
    
    data["users"][target]["total"] -= jumlah
    data["users"][target]["accounts"] = data["users"][target]["accounts"][jumlah:]
    save_data(data)
    
    nominal = jumlah * data.get('price', DEFAULT_PRICE)
    await update.message.reply_text(f"✅ Payout Rp {nominal:,}\nSisa: {data['users'][target]['total']} akun")

async def all_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Hanya admin!")
        return
    
    text = "📋 SEMUA USER:\n\n"
    for uid, info in data["users"].items():
        if info["total"] > 0:
            text += f"UID: {uid}\nDANA: {info['dana']}\nTotal: {info['total']} akun\n\n"
    
    await update.message.reply_text(text if len(text) < 4000 else "Terlalu banyak data")

# ================= HANDLE COOKIE =================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # cek dana
    if user_id not in user_dana:
        await update.message.reply_text("⚠️ Set DANA dulu: /setdana 08xxxx")
        return

    text = update.message.text
    uid = extract_uid(text)

    # jika bukan cookie
    if not uid:
        return

    # simpan data
    success = save_data(
        user_id,
        update.effective_user.username,
        user_dana[user_id],
        uid
    )

    if success:
        waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        df = pd.read_excel(FILE)
        total_cookie = len(df)

        # NOTIF USER
        await update.message.reply_text(f"""✓ BERHASIL DISIMPAN!
ID: {uid}
Total Cookies: {total_cookie}
Sisa slot: UNLIMITED
""")

        # NOTIF ADMIN
        text_admin = f"""📥 STOR BARU

👤 User: @{update.effective_user.username}
🆔 ID: {user_id}
💰 DANA: {user_dana[user_id]}
🔑 UID: {uid}
🕒 Waktu: {waktu}
"""

        await context.bot.send_message(chat_id=ADMIN_ID, text=text_admin)

    else:
        await update.message.reply_text("⚠️ UID sudah ada (duplikat)")

# ================= RUN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("setdana", setdana))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("allstats", allstats))
app.add_handler(CommandHandler("downloadexcel", download_excel))
app.add_handler(CommandHandler("resetexcel", reset_excel))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("BOT RUNNING...")
app.run_polling()
