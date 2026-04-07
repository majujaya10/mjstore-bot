import re
import pandas as pd
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ================= CONFIG =================
TOKEN = "8655740459:AAHHLBwXecY377lkSdLnNlRZMLC5TOPR1VU"
PASSWORD = "Cikawe125"
ADMIN_IDS = [5312657021]
FILE = "data.xlsx"

# ================= INIT EXCEL =================
try:
    df = pd.read_excel(FILE)
except:
    df = pd.DataFrame(columns=["user_id","username","dana","uid","waktu"])
    df.to_excel(FILE, index=False)

user_dana = {}
logged_in_users = set()

# ================= UTIL =================
def extract_uid(text):
    match = re.search(r"c_user=(\\d+)", text)
    return match.group(1) if match else None

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🤖 WELCOME MJSTORE10\nPassword: {PASSWORD}\nGunakan /login <password>")

# ================= LOGIN =================
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if context.args[0] == PASSWORD:
            logged_in_users.add(update.effective_user.id)
            await update.message.reply_text("✅ Login berhasil")
        else:
            await update.message.reply_text("❌ Password salah")
    except:
        await update.message.reply_text("Gunakan: /login password")

# ================= SET PASSWORD =================
async def setpassword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PASSWORD
    if update.effective_user.id not in ADMIN_IDS:
        return
    try:
        PASSWORD = context.args[0]
        await update.message.reply_text(f"✅ Password diubah: {PASSWORD}")
    except:
        await update.message.reply_text("Gunakan: /setpassword passwordbaru")

# ================= SET DANA =================
async def set_dana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in logged_in_users:
        await update.message.reply_text("🔒 Login dulu /login")
        return
    try:
        user_dana[update.effective_user.id] = context.args[0]
        await update.message.reply_text("✅ DANA disimpan")
    except:
        await update.message.reply_text("Gunakan: /setdana 08xxxx")

# ================= HANDLE COOKIE =================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username

    if user_id not in logged_in_users:
        await update.message.reply_text("🔒 Login dulu /login")
        return

    if user_id not in user_dana:
        await update.message.reply_text("❌ Set DANA dulu")
        return

    uid = extract_uid(update.message.text)
    if not uid:
        await update.message.reply_text("❌ UID tidak ditemukan")
        return

    df = pd.read_excel(FILE)

    if uid in df['uid'].astype(str).values:
        await update.message.reply_text("⚠️ UID sudah ada")
        return

    waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    df = pd.concat([df, pd.DataFrame([{
        "user_id": user_id,
        "username": username,
        "dana": user_dana[user_id],
        "uid": uid,
        "waktu": waktu
    }])])

    df.to_excel(FILE, index=False)

    await update.message.reply_text(f"✅ UID {uid} masuk")

    for admin in ADMIN_IDS:
        await context.bot.send_message(chat_id=admin, text=f"📥 UID: {uid}\nUser: @{username}")

# ================= STATS =================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    df = pd.read_excel(FILE)
    total = len(df[df['user_id'] == update.effective_user.id])
    await update.message.reply_text(f"📊 Stor kamu: {total}")

async def allstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    df = pd.read_excel(FILE)
    await update.message.reply_text(f"📊 Total semua: {len(df)}")

# ================= LIVE =================
async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    df = pd.read_excel(FILE)
    user_df = df[df['user_id'] == update.effective_user.id]
    if user_df.empty:
        await update.message.reply_text("Belum ada data")
        return
    file_name = f"live_{update.effective_user.id}.xlsx"
    user_df.to_excel(file_name, index=False)
    await update.message.reply_document(open(file_name, 'rb'))

# ================= RESET =================
async def reset_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    pd.DataFrame(columns=["user_id","username","dana","uid","waktu"]).to_excel(FILE, index=False)
    await update.message.reply_text("✅ Excel direset")

async def resetstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    global user_dana
    user_dana = {}
    await update.message.reply_text("✅ Stats direset")

# ================= RUN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("login", login))
app.add_handler(CommandHandler("setpassword", setpassword))
app.add_handler(CommandHandler("setdana", set_dana))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("allstats", allstats))
app.add_handler(CommandHandler("live", live))
app.add_handler(CommandHandler("resetexcel", reset_excel))
app.add_handler(CommandHandler("resetstats", resetstats))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

app.run_polling()
