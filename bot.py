import json
import os
import asyncio
import re
from datetime import datetime
from typing import Dict, List
import requests
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import NetworkError, TimedOut, RetryAfter

# ============ KONFIGURASI (GANTI DI SINI) ============
import os

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN belum diset di Railway Variables!")
ADMIN_ID = 5312657021
FILE = "data.xlsx"

# Konfigurasi timeout & retry
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

# Konfigurasi default
DEFAULT_PRICE = 1100
DEFAULT_LABEL = "frenta76"
DEFAULT_SLOT = 103
DEFAULT_RULES = "📋 Kirim UID Facebook 1 per baris. Pastikan UID valid dan aktif. Dilarang setor UID yang sudah pernah disetor!"

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
                # Pastikan semua key ada
                if "rules" not in data:
                    data["rules"] = DEFAULT_RULES
                if "label" not in data:
                    data["label"] = DEFAULT_LABEL
                if "price" not in data:
                    data["price"] = DEFAULT_PRICE
                if "global_slot" not in data:
                    data["global_slot"] = DEFAULT_SLOT
                if "job_active" not in data:
                    data["job_active"] = True
                if "users" not in data:
                    data["users"] = {}
                
                # Migrasi data user
                for uid, user_data in data["users"].items():
                    if "slot" not in user_data:
                        user_data["slot"] = data.get("global_slot", DEFAULT_SLOT)
                    if "accounts" not in user_data:
                        user_data["accounts"] = []
                    if "total" not in user_data:
                        user_data["total"] = len(user_data["accounts"])
                    if "dana" not in user_data:
                        user_data["dana"] = ""
                return data
        except Exception as e:
            print(f"Error loading data: {e}")
            return get_default_data()
    return get_default_data()

def save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving data: {e}")

data = load_data()

# ============ FUNGSI CEK LIVE FACEBOOK ============
def check_facebook_live(uid: str) -> Dict:
    url = f"https://www.facebook.com/{uid}"
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                url, 
                timeout=REQUEST_TIMEOUT,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                allow_redirects=True
            )
            
            text_lower = response.text.lower()
            
            if response.status_code == 200:
                if "checkpoint" in text_lower or "login_required" in text_lower or "verify" in text_lower:
                    return {"status": "⚠️ CHECKPOINT", "emoji": "⚠️", "live": False}
                elif "content not found" in text_lower or "sorry" in text_lower or "page not found" in text_lower:
                    return {"status": "❌ TIDAK DITEMUKAN", "emoji": "❌", "live": False}
                elif "profile" in text_lower or "facebook.com" in text_lower or "id=" in text_lower:
                    return {"status": "✅ LIVE", "emoji": "✅", "live": True}
                else:
                    return {"status": "❓ UNKNOWN", "emoji": "❓", "live": False}
            elif response.status_code == 404:
                return {"status": "❌ TIDAK DITEMUKAN", "emoji": "❌", "live": False}
            else:
                return {"status": f"⚠️ ERROR {response.status_code}", "emoji": "⚠️", "live": False}
                
        except requests.exceptions.Timeout:
            if attempt == MAX_RETRIES - 1:
                return {"status": "⏰ TIMEOUT", "emoji": "⏰", "live": False}
            continue
        except Exception:
            if attempt == MAX_RETRIES - 1:
                return {"status": "⚠️ ERROR", "emoji": "⚠️", "live": False}
            continue
    
    return {"status": "⚠️ UNKNOWN", "emoji": "⚠️", "live": False}

def check_multiple_uids(uids: List[str]) -> List[Dict]:
    results = []
    for idx, uid in enumerate(uids):
        uid_clean = uid.strip()
        if uid_clean.isdigit() and len(uid_clean) >= 5:
            result = check_facebook_live(uid_clean)
            result["uid"] = uid_clean
            results.append(result)
        else:
            results.append({"uid": uid_clean, "status": "❌ INVALID", "emoji": "❌", "live": False})
        
        if (idx + 1) % 10 == 0:
            asyncio.sleep(0.3)
    
    return results

# ============ FUNGSI HELPER ============
def get_user_slot(user_id: str) -> int:
    if user_id not in data["users"]:
        return data.get("global_slot", DEFAULT_SLOT)
    return data["users"][user_id].get("slot", data.get("global_slot", DEFAULT_SLOT))

def get_remaining_slot(user_id: str) -> int:
    user_slot = get_user_slot(user_id)
    if user_id not in data["users"]:
        return user_slot
    used = len(data["users"][user_id].get("accounts", []))
    return max(0, user_slot - used)

def get_total_used_slots() -> int:
    total = 0
    for user_data in data["users"].values():
        total += len(user_data.get("accounts", []))
    return total

# ============ HANDLER USER ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    username = update.effective_user.first_name
    
    if user_id not in data["users"]:
        data["users"][user_id] = {
            "dana": "", 
            "total": 0, 
            "accounts": [],
            "slot": data.get("global_slot", DEFAULT_SLOT)
        }
        save_data(data)
    
    user_data = data["users"][user_id]
    user_slot = get_user_slot(user_id)
    remaining_slot = get_remaining_slot(user_id)
    total_used = get_total_used_slots()
    
    text = f"""👋 Halo {username}!

📋 RULES:
{data.get('rules', DEFAULT_RULES)}

📊 Info Setoranmu:
├ Total Akun: {user_data['total']}
├ Slot Pribadi: {user_slot}
├ Slot Terpakai: {len(user_data['accounts'])}/{user_slot}
└ Sisa Slot: {remaining_slot}

📌 Info Panel:
├ Label (PW): {data.get('label', DEFAULT_LABEL)}
├ Harga/Akun: Rp {data.get('price', DEFAULT_PRICE):,}
└ Total Slot Terpakai: {total_used}

🛠 Menu User:
/setdana <nomor> - Set nomor DANA (wajib!)
/ceklive - Cek live UID (kirim UID per baris)
/live - Download rekapan setoranmu

⚠️ Kirim UID langsung untuk setor (max {user_slot} akun)
📝 Format setor: 
61683838484822
61583883838383
61578399339393
(1 UID per baris)"""
    
    await update.message.reply_text(text)

async def set_dana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not context.args:
        await update.message.reply_text("❌ Format: /setdana <nomor_telepon>\nContoh: /setdana 08123456789")
        return
    
    nomor = context.args[0]
    if not nomor.isdigit() or len(nomor) < 10:
        await update.message.reply_text("❌ Nomor tidak valid! Masukkan nomor telepon yang benar (min 10 digit).")
        return
    
    if user_id not in data["users"]:
        data["users"][user_id] = {
            "dana": "", 
            "total": 0, 
            "accounts": [],
            "slot": data.get("global_slot", DEFAULT_SLOT)
        }
    
    data["users"][user_id]["dana"] = nomor
    save_data(data)
    await update.message.reply_text(f"✅ Nomor DANA berhasil diatur ke: {nomor}\nSekarang kamu bisa mulai setor akun! 🚀")

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules_text = data.get("rules", DEFAULT_RULES)
    
    text = f"""📋 RULES TERBARU:
━━━━━━━━━━━━━━━━━━━━━
{rules_text}
━━━━━━━━━━━━━━━━━━━━━"""
    
    await update.message.reply_text(text)
    
async def cek_live_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 Kirimkan UID yang ingin dicek (1 UID per baris, max 200 UID):\n\nContoh:\n61683838484822\n61583883838383\n61578399339393")
    context.user_data["waiting_for_uid_check"] = True

async def handle_uid_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text.strip()
    context.user_data["waiting_for_uid_check"] = False
    
    lines = message_text.split('\n')
    uids = []
    for line in lines:
        line = line.strip()
        if line.isdigit() and len(line) >= 5:
            uids.append(line)
    
    if not uids:
        await update.message.reply_text("❌ Tidak ditemukan UID valid. Kirimkan angka UID (min 5 digit).")
        return
    
    if len(uids) > 200:
        await update.message.reply_text(f"⚠️ Terlalu banyak UID ({len(uids)}). Maksimal 200 UID.")
        return
    
    status_msg = await update.message.reply_text(f"🔄 Mengecek {len(uids)} UID... Mohon tunggu.")
    
    results = check_multiple_uids(uids)
    
    live_count = sum(1 for r in results if r.get("live", False))
    checkpoint_count = sum(1 for r in results if "CHECKPOINT" in r.get("status", ""))
    not_found_count = sum(1 for r in results if "TIDAK DITEMUKAN" in r.get("status", ""))
    
    result_text = f"📊 HASIL CEK LIVE\n━━━━━━━━━━━━━━━━━━━━━\n"
    result_text += f"✅ LIVE: {live_count}\n"
    result_text += f"⚠️ CHECKPOINT: {checkpoint_count}\n"
    result_text += f"❌ TIDAK DITEMUKAN: {not_found_count}\n"
    result_text += f"📦 TOTAL: {len(results)} UID\n"
    result_text += f"━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for r in results:
        result_text += f"{r['emoji']} {r['uid']}: {r['status']}\n"
    
    if len(result_text) > 4000:
        filename = f"ceklive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(result_text)
        await update.message.reply_document(document=open(filename, 'rb'), caption=f"📄 Hasil cek {len(results)} UID")
        os.remove(filename)
    else:
        await update.message.reply_text(result_text)
    
    await status_msg.delete()

async def handle_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    message_text = update.message.text.strip()
    
    if context.user_data.get("waiting_for_uid_check"):
        await handle_uid_check(update, context)
        return
    
    if not data.get("job_active", True):
        await update.message.reply_text("⛔ JOB SEDANG DITUTUP. Silahkan coba lagi nanti.")
        return
    
    if user_id not in data["users"] or not data["users"][user_id].get("dana"):
        await update.message.reply_text("❌ Kamu belum /setdana! Ketik /setdana <nomor> dulu ya!")
        return
    
    lines = message_text.split('\n')
    uids = []
    for line in lines:
        line = line.strip()
        if line.isdigit() and len(line) >= 5:
            uids.append(line)
    
    if not uids:
        return
    
    user_slot = get_user_slot(user_id)
    if len(uids) > user_slot:
        await update.message.reply_text(f"⚠️ Slot kamu hanya {user_slot}. Tidak bisa setor {len(uids)} akun sekaligus.")
        return
    
    remaining_slot = get_remaining_slot(user_id)
    if remaining_slot < len(uids):
        await update.message.reply_text(f"⚠️ Sisa slot kamu hanya {remaining_slot}.")
        return
    
    status_msg = await update.message.reply_text(f"🔄 Memproses {len(uids)} UID...")
    
    success_count = 0
    results_text = "📥 HASIL SETORAN\n━━━━━━━━━━━━━━━━━━━━━\n"
    live_count = 0
    checkpoint_count = 0
    
    for uid in uids:
        live_result = check_facebook_live(uid)
        
        data["users"][user_id]["accounts"].append({
            "uid": uid,
            "status": live_result["status"],
            "timestamp": datetime.now().isoformat()
        })
        data["users"][user_id]["total"] += 1
        success_count += 1
        
        if live_result["live"]:
            live_count += 1
        elif "CHECKPOINT" in live_result["status"]:
            checkpoint_count += 1
        
        results_text += f"{live_result['emoji']} {uid}: {live_result['status']}\n"
        
        owner_text = f"📥 SETORAN\nDari: {update.effective_user.first_name}\nDANA: {data['users'][user_id]['dana']}\nUID: {uid}\nStatus: {live_result['status']}"
        try:
            await context.bot.send_message(chat_id=OWNER_ID, text=owner_text)
        except:
            pass
        
        await asyncio.sleep(0.2)
    
    save_data(data)
    
    results_text += f"\n━━━━━━━━━━━━━━━━━━━━━\n"
    results_text += f"✅ LIVE: {live_count}\n"
    results_text += f"⚠️ CHECKPOINT: {checkpoint_count}\n"
    results_text += f"📊 Berhasil: {success_count}/{len(uids)} akun\n"
    results_text += f"📦 Total akunmu: {data['users'][user_id]['total']}\n"
    results_text += f"📌 Sisa slot: {get_remaining_slot(user_id)}"
    
    await status_msg.delete()
    await update.message.reply_text(results_text)

async def live_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in data["users"] or data["users"][user_id]["total"] == 0:
        await update.message.reply_text("📭 Kamu belum menyetor akun.")
        return
    
    user_data = data["users"][user_id]
    filename = f"rekapan_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    content = f"""REKAPAN SETORAN
UID Telegram: {user_id}
Nama: {update.effective_user.first_name}
Nomor DANA: {user_data['dana']}
Total Akun: {user_data['total']}
Slot: {get_user_slot(user_id)}
Tanggal: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

DAFTAR AKUN:
"""
    for i, acc in enumerate(user_data["accounts"], 1):
        content += f"{i}. {acc['uid']} - {acc['status']} - {acc['timestamp']}\n"
    
    total_nominal = user_data['total'] * data.get('price', DEFAULT_PRICE)
    content += f"\nTotal Nominal: Rp {total_nominal:,}"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    await update.message.reply_document(document=open(filename, 'rb'), caption="📄 Rekapan setoranmu")
    os.remove(filename)

# ============ ADMIN COMMANDS ============
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

# ============ MAIN ============
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
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
