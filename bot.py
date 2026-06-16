import telebot
from telebot import types
import sqlite3
import os
import subprocess
import json
from datetime import datetime, timedelta

TOKEN = '8349352122:AAGruAqf3nw-8v-soajHMTAuTIYRM3WLu7w'
bot = telebot.TeleBot(TOKEN)

# Yönetici ID'niz
ADMIN_ID = 8349352122  

# Bulut sunucuları için veritabanı yolu
db_path = os.path.join("/tmp", "medya.db") if os.path.exists("/tmp") else "medya.db"
conn = sqlite3.connect(db_path, check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    daily_limit INTEGER DEFAULT 4,
    last_active TEXT,
    is_vip INTEGER DEFAULT 0,
    vip_expire TEXT DEFAULT 'Yok'
)
""")
conn.commit()

user_links = {}

# ---------------- SÜRE VE LİMİT KONTROL MOTORU ----------------
def get_or_create_user(uid):
    bugun_dt = datetime.now()
    bugun = bugun_dt.strftime("%Y-%m-%d")
    
    cur.execute("SELECT * FROM users WHERE id=?", (uid,))
    user = cur.fetchone()
    
    if not user:
        cur.execute("INSERT INTO users (id, daily_limit, last_active, is_vip, vip_expire) VALUES (?, 4, ?, 0, 'Yok')", (uid, bugun))
        conn.commit()
        return {"id": uid, "limit": 4, "is_vip": 0, "expire": "Yok"}
    
    is_vip = user[3]
    vip_expire = user[4]
    
    if is_vip == 1 and vip_expire != 'Yok':
        expire_dt = datetime.strptime(vip_expire, "%Y-%m-%d")
        if bugun_dt > expire_dt:
            is_vip = 0
            vip_expire = 'Yok'
            cur.execute("UPDATE users SET is_vip=0, vip_expire='Yok', daily_limit=4 WHERE id=?", (uid,))
            conn.commit()
            try:
                bot.send_message(uid, "⚠️ *VIP Süreniz Doldu!* Hesabınız standart moda düşürülmüştür. Yenilemek için: @Vexsonstore", parse_mode="Markdown")
            except:
                pass

    if user[2] != bugun:
        yeni_limit = 4 if is_vip == 0 else 9999
        cur.execute("UPDATE users SET daily_limit=?, last_active=? WHERE id=?", (yeni_limit, bugun, uid))
        conn.commit()
        return {"id": uid, "limit": yeni_limit, "is_vip": is_vip, "expire": vip_expire}
        
    return {"id": uid, "limit": user[1], "is_vip": is_vip, "expire": vip_expire}

def limit_dus(uid):
    cur.execute("UPDATE users SET daily_limit = daily_limit - 1 WHERE id=?", (uid,))
    conn.commit()

def vip_sureli_ekle(hedef_id, gun_sayisi):
    bugun_dt = datetime.now()
    bitis_dt = bugun_dt + timedelta(days=gun_sayisi)
    bitis_tarihi = bitis_dt.strftime("%Y-%m-%d")
    bugun = bugun_dt.strftime("%Y-%m-%d")
    
    cur.execute("SELECT * FROM users WHERE id=?", (hedef_id,))
    user = cur.fetchone()
    
    if user:
        cur.execute("UPDATE users SET is_vip=1, daily_limit=9999, vip_expire=? WHERE id=?", (bitis_tarihi, hedef_id))
    else:
        cur.execute("INSERT INTO users (id, daily_limit, last_active, is_vip, vip_expire) VALUES (?, 9999, ?, 1, ?)", (hedef_id, bugun, bitis_tarihi))
    conn.commit()
    return bitis_tarihi

# ---------------- YT-DLP DOĞRUDAN İNDİRME FONKSİYONU ----------------
def yt_dlp_link_coz(url, format_type="video"):
    try:
        cmd = ["yt-dlp", "-j", url]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        video_info = json.loads(result.stdout)
        return {"status": "success", "url": video_info.get("url")}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ---------------- ADMIN SÜRELİ VIP EKLEME KOMUTLARI ----------------
@bot.message_handler(commands=['vip_hafta', 'vip_ay'])
def admin_vip_komutlari(message):
    cid = message.chat.id
    if cid != ADMIN_ID:
        bot.send_message(cid, "❌ Yetkiniz yok!")
        return

    komut = message.text.split()
    if len(komut) < 2:
        bot.send_message(cid, f"⚠️ Kullanım:\n`/vip_hafta KULLANICI_ID`\n`/vip_ay KULLANICI_ID`", parse_mode="Markdown")
        return

    hedef_id = komut[1]
    if not毀 hedef_id.isdigit():
        bot.send_message(cid, "❌ Geçersiz ID!")
        return

    hedef_id = int(hedef_id)
    gun = 7 if "hafta" in komut[0] else 30
    sure_adi = "Haftalık" if gun == 7 else "Aylık"
    
    bitis = vip_sureli_ekle(hedef_id, gun)
    bot.send_message(cid, f"👑 `{hedef_id}` başarıyla **{sure_adi} VIP** yapıldı!\n📅 Bitiş: `{bitis}`", parse_mode="Markdown")
    try:
        bot.send_message(hedef_id, f"👑 *Tebrikler!* Hesabınız @Vexsonstore tarafından **{sure_adi} VIP** yapıldı!\n📅 Bitiş: `{bitis}`", parse_mode="Markdown")
    except:
        pass

# ---------------- START KOMUTU ----------------
@bot.message_handler(commands=['start'])
def start(message):
    cid = message.chat.id
    u = get_or_create_user(cid)
    
    statü = "👑 VIP Üye" if u["is_vip"] == 1 else "🆓 Standart Üye"
    limit_metni = "Sınırsız" if u["is_vip"] == 1 else f"{u['limit']} işlem"
    sure_metni = f"\n📅 VIP Bitiş: `{u['expire']}`" if u["is_vip"] == 1 else ""
    
    bot.send_message(
        cid,
        f"👋 Salam {message.from_user.first_name or 'Kullanıcı'}!\n"
        f"🆔 *Bot ID'niz:* `{cid}` (VIP olmak için admine gönderin)\n\n"
        f"📊 *Mevcut Durumunuz:* {statü}{sure_metni}\n"
        f"🔋 *Kalan Günlük Limitiniz:* {limit_metni}\n\n"
        f"📥 Başlamak için bota bir **TikTok** veya **Instagram** linki gönderin!",
        parse_mode="Markdown"
    )

# ---------------- LİNK İŞLEME VE BUTONLAR ----------------
@bot.message_handler(func=lambda message: True)
def link_yakala(message):
    url = message.text.strip()
    cid = message.chat.id
    u = get_or_create_user(cid)

    if u["limit"] <= 0 and u["is_vip"] == 0:
        bot.send_message(cid, "❌ Günlük limitiniz (4/4) dolmuştur! VIP için yetkili: @Vexsonstore")
        return

    if "instagram.com" in url or "tiktok.com" in url:
        user_links[cid] = url
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            types.InlineKeyboardButton("🎬 Videoyu İndir (Standart HD)", callback_data="motor_video"),
            types.InlineKeyboardButton("🎵 Sadece Sesi Ayır ve İndir (MP3)", callback_data="motor_audio"),
            types.InlineKeyboardButton("👑 4K / 8K Ultra Kalitede İndir (VIP)", callback_data="motor_vip")
        )
        bot.send_message(cid, "📥 Link algılandı. Ne yapmak istersiniz?", reply_markup=kb)
    else:
        bot.send_message(cid, "❌ Geçersiz link!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("motor_"))
def islem_yap(call):
    cid = call.message.chat.id
    islem = call.data
    u = get_or_create_user(cid)

    if u["limit"] <= 0 and u["is_vip"] == 0:
        bot.send_message(cid, "❌ Limit yetersiz.")
        return

    if cid not in user_links:
        bot.send_message(cid, "❌ Link zaman aşımına uğradı.")
        return
        
    hedef_url = user_links[cid]
    
    if islem == "motor_vip" and u["is_vip"] == 0:
        bot.send_message(cid, "⚠️ Bu özellik sadece *VIP Mod* kullanıcılarına özeldir! İletişim: @Vexsonstore")
        return

    bot.edit_message_text("⏳ Gelişmiş indirme sistemi dosyayı çözüyor... Lütfen bekleyin.", cid, call.message.message_id)
    
    format_tipi = "audio" if islem == "motor_audio" else "video"
    sonuc = yt_dlp_link_coz(hedef_url, format_tipi)
    
    if sonuc["status"] == "error":
        bot.send_message(cid, "❌ Medya dosyası çözülemedi. Linkin gizli veya silinmiş olmadığından emin olun.")
        if cid in user_links: del user_links[cid]
        return

    direkt_link = sonuc["url"]
    
    try:
        if islem == "motor_video":
            bot.send_chat_action(cid, 'upload_video')
            bot.send_video(cid, direkt_link, caption="🎬 Standart HD Videonuz Hazır! | Yetkili: @Vexsonstore")
            if u["is_vip"] == 0: limit_dus(cid)

        elif islem == "motor_audio":
            bot.send_chat_action(cid, 'upload_audio')
            bot.send_audio(cid, direkt_link, caption="🎵 Sesi Ayıklandı! | Yetkili: @Vexsonstore")
            if u["is_vip"] == 0: limit_dus(cid)

        elif islem == "motor_vip" and u["is_vip"] == 1:
            bot.send_chat_action(cid, 'upload_video')
            bot.send_video(cid, direkt_link, caption="👑 VIP Ultra Kalite (Orijinal Ham Veri) Hazır!")

        del user_links[cid]
        
    except Exception as e:
        bot.send_message(cid, "❌ Dosya Telegram'a yüklenirken bir hata oluştu. Lütfen tekrar deneyin.")
        if cid in user_links: del user_links[cid]

if __name__ == "__main__":
    bot.polling(none_stop=True)
