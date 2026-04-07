import re
import pandas as pd
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ================= CONFIG =================
TOKEN = "8655740459:AAHHLBwXecY377lkSdLnNlRZMLC5TOPR1VU"
ADMIN_ID = 5312657021
FILE = "data.xlsx"

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
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """🤖 WELCOME TO MJSTORE10

📝 Kirim cookies untuk ambil UID

📌 WAJIB:
Gunakan:
/setdana 08xxxx

Setelah itu kirim cookies"""
    await update.message.reply_text(text)

async def setdana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Gunakan: /setdana 08xxxx")
        return

    dana = context.args[0]
    user_dana[update.effective_user.id] = dana
    await update.message.reply_text(f"✅ DANA disimpan: {dana}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    df = pd.read_excel(FILE)
    user_id = update.effective_user.id
    total = len(df[df["user_id"] == user_id])

    await update.message.reply_text(f"📊 Total setoran kamu: {total}")

async def allstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    df = pd.read_excel(FILE)
    await update.message.reply_text(f"📊 Total semua data: {len(df)}")

async def download_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_document(open(FILE, "rb"))

async def reset_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    df = pd.DataFrame(columns=["user_id", "username", "dana", "uid", "waktu"])
    df.to_excel(FILE, index=False)

    await update.message.reply_text("♻️ Excel berhasil direset!")

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
