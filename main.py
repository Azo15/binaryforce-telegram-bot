import os
import sys
import json
import time
import threading
from datetime import datetime, timedelta
import requests
import telebot
from dotenv import load_dotenv

# Windows konsolunda Unicode/Emoji çıktı hatasını önlemek için stdout kodlamasını ayarla
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# .env ortam değişkenlerini yükle
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    print("❌ HATA: 'BOT_TOKEN' bulunamadı veya varsayılan değerde bırakıldı.")
    sys.exit(1)

# PythonAnywhere ortamında proxy yapılandırmasını otomatik uygula
HTTP_PROXY = os.getenv("http_proxy") or os.getenv("HTTPS_PROXY")
if HTTP_PROXY:
    telebot.apihelper.proxy = {'http': HTTP_PROXY, 'https': HTTP_PROXY}
    print(f"ℹ️ PythonAnywhere Proxy ayarlandı: {HTTP_PROXY}")

bot = telebot.TeleBot(BOT_TOKEN)

# PythonAnywhere üzerindeki geçici proxy hatalarına (503 Service Unavailable vb.) karşı otomatik yeniden deneme (Retry) mekanizması
_original_reply_to = bot.reply_to
_original_send_message = bot.send_message

def safe_reply_to(message, text, **kwargs):
    for i in range(3):
        try:
            return _original_reply_to(message, text, **kwargs)
        except Exception as e:
            print(f"⚠️ Yanıt gönderilemedi, yeniden deneniyor ({i+1}/3)... Hata: {e}")
            if i < 2:
                time.sleep(1.5)
    raise e

def safe_send_message(chat_id, text, **kwargs):
    for i in range(3):
        try:
            return _original_send_message(chat_id, text, **kwargs)
        except Exception as e:
            print(f"⚠️ Mesaj gönderilemedi, yeniden deneniyor ({i+1}/3)... Hata: {e}")
            if i < 2:
                time.sleep(1.5)
    raise e

bot.reply_to = safe_reply_to
bot.send_message = safe_send_message

DEFAULT_CITY = "Kırklareli"
SUBSCRIBERS_FILE = "subscribers.json"
sent_reminders = set()  # Bugün gönderilen hatırlatmaların takibi (Örn: "2026-07-21_İkindi")


# --- ABONE YÖNETİMİ ---
def load_subscribers():
    """Abone chat_id'lerini dosyadan okur."""
    if os.path.exists(SUBSCRIBERS_FILE):
        try:
            with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_subscriber(chat_id):
    """Yeni abone ekler ve kaydeder."""
    subscribers = load_subscribers()
    if chat_id not in subscribers:
        subscribers.add(chat_id)
        try:
            with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
                json.dump(list(subscribers), f)
        except Exception as e:
            print(f"Abone kaydedilirken hata: {e}")


# --- EZAN VAKİTLERİ VE HAVA DURUMU YARDIMCILARI ---
def get_prayer_times(city=DEFAULT_CITY):
    """
    Aladhan API kullanarak şehir bazlı namaz vakitlerini çeker.
    """
    try:
        url = f"https://api.aladhan.com/v1/timingsByCity?city={city}&country=Turkey&method=13"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and data.get("code") == 200:
                timings = data["data"]["timings"]
                return timings
    except Exception as e:
        print(f"Ezan vakti çekilirken hata ({city}): {e}")
    return None


def get_weather(city=DEFAULT_CITY):
    """
    wttr.in API kullanarak Türkçe hava durumu verilerini çeker.
    """
    try:
        url = f"https://wttr.in/{city}?format=j1&lang=tr"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            curr = data["current_condition"][0]
            temp = curr.get("temp_C", "-")
            feels = curr.get("FeelsLikeC", "-")
            humidity = curr.get("humidity", "-")
            wind = curr.get("windspeedKmph", "-")

            desc = "Açık / Güneşli"
            if "lang_tr" in curr and curr["lang_tr"]:
                desc = curr["lang_tr"][0].get("value", desc)
            elif "weatherDesc" in curr and curr["weatherDesc"]:
                desc = curr["weatherDesc"][0].get("value", desc)

            return {
                "city": city.title(),
                "temp": temp,
                "feels": feels,
                "humidity": humidity,
                "wind": wind,
                "desc": desc
            }
    except Exception as e:
        print(f"Hava durumu çekilirken hata ({city}): {e}")
    return None


def get_date_info():
    """
    Güncel tarih, gün ve saat bilgisini Türkçe biçimlendirir.
    """
    now = datetime.now()
    months = [
        "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
        "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
    ]
    days = [
        "Pazartesi", "Salı", "Çarşamba", "Perşembe",
        "Cuma", "Cumartesi", "Pazar"
    ]

    day_str = now.strftime("%d")
    month_str = months[now.month - 1]
    year_str = now.strftime("%Y")
    day_name = days[now.weekday()]
    time_str = now.strftime("%H:%M:%S")

    return (
        f"📅 *Güncel Tarih ve Saat Bilgisi*\n\n"
        f"📆 *Tarih:* {day_str} {month_str} {year_str}\n"
        f"🗓️ *Gün:* {day_name}\n"
        f"⏰ *Saat:* {time_str}"
    )


# --- 10 DAKİKA ÖNCE EZAN HATIRLATICI ZAMANLAYICISI ---
def start_reminder_scheduler():
    """
    Arka planda 30 saniyede bir çalışarak Kırklareli namaz vakitlerine 10 dakika kala abonelere bildirim atar.
    """
    def reminder_loop():
        global sent_reminders
        while True:
            try:
                now = datetime.now()
                today_str = now.strftime("%Y-%m-%d")
                current_time_str = now.strftime("%H:%M")

                # Namaz vakitlerini al
                timings = get_prayer_times(DEFAULT_CITY)
                if timings:
                    prayer_mapping = {
                        "İmsak": timings.get("Fajr"),
                        "Güneş": timings.get("Sunrise"),
                        "Öğle": timings.get("Dhuhr"),
                        "İkindi": timings.get("Asr"),
                        "Akşam": timings.get("Maghrib"),
                        "Yatsı": timings.get("Isha")
                    }

                    for name, p_time in prayer_mapping.items():
                        if not p_time:
                            continue

                        # Vakit saatini datetime objesine dönüştür
                        try:
                            p_hours, p_mins = map(int, p_time.split(":"))
                            p_datetime = now.replace(hour=p_hours, minute=p_mins, second=0, microsecond=0)
                            
                            # 10 dakika öncesi vakti hesapla
                            reminder_time = p_datetime - timedelta(minutes=10)
                            reminder_time_str = reminder_time.strftime("%H:%M")

                            reminder_key = f"{today_str}_{name}"

                            # Şu an hatırlatma saati geldiyse ve bugün henüz gönderilmediyse
                            if current_time_str == reminder_time_str and reminder_key not in sent_reminders:
                                sent_reminders.add(reminder_key)
                                subscribers = load_subscribers()

                                reminder_msg = (
                                    f"⏰ *Namaz Vakti Hatırlatması!*\n\n"
                                    f"🕌 *{DEFAULT_CITY}* için *{name}* namazına 10 dakika kaldı.\n"
                                    f"⏱️ *Namaz Vakti:* `{p_time}`"
                                )

                                for chat_id in subscribers:
                                    try:
                                        bot.send_message(chat_id, reminder_msg, parse_mode="Markdown")
                                    except Exception as send_err:
                                        print(f"Mesaj gönderilemedi ({chat_id}): {send_err}")
                        except Exception as parse_err:
                            print(f"Vakit ayrıştırma hatası ({name}): {parse_err}")

            except Exception as loop_err:
                print(f"Hatırlatıcı döngü hatası: {loop_err}")

            time.sleep(30)  # 30 saniye bekle

    thread = threading.Thread(target=reminder_loop, daemon=True)
    thread.start()


# --- KOMUT İŞLEYİCİLERİ ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """
    /start komutu: Karşılama ve kullanıcıyı abona listesine kaydetme.
    """
    save_subscriber(message.chat.id)
    welcome_message = (
        "Merhaba! BinaryForce Telegram Botu'na hoş geldin. "
        "Komutları görmek için /help yazabilirsin."
    )
    bot.reply_to(message, welcome_message)


@bot.message_handler(commands=['help'])
def send_help(message):
    """
    /help komutu: Tüm komutların listesi.
    """
    save_subscriber(message.chat.id)
    help_message = (
        "🤖 *BinaryForce Telegram Bot Komut Rehberi*\n\n"
        "🔹 /start - Botu başlatır ve karşılama mesajı gösterir.\n"
        "🔹 /help - Tüm komutları listeler.\n"
        "🔹 /ezan [şehir] - Namaz vakitlerini gösterir (Varsayılan: Kırklareli).\n"
        "🔹 /tarih - Güncel tarih ve saat bilgisini gösterir.\n"
        "🔹 /hava [şehir] - Anlık hava durumunu gösterir (Varsayılan: Kırklareli).\n"
        "🔹 /echo <metin> - Yazdığınız metni yansıtır.\n\n"
        "⏰ *Otomatik Bildirim:* Kırklareli ezan vakitlerine 10 dakika kala otomatik hatırlatma alırsınız!\n\n"
        "💬 *Akıllı Sohbet:* Bana 'hava nasıl', 'ezan kaçta', 'tarih ne' veya 'nasılsın' yazabilirsiniz!"
    )
    bot.reply_to(message, help_message, parse_mode="Markdown")


@bot.message_handler(commands=['ezan', 'vakit'])
def handle_ezan(message):
    """
    /ezan veya /vakit [şehir] komutu işleyicisi.
    """
    save_subscriber(message.chat.id)
    command_args = message.text.split(maxsplit=1)
    city = command_args[1].strip() if len(command_args) > 1 else DEFAULT_CITY

    timings = get_prayer_times(city)
    if timings:
        msg = (
            f"🕌 *{city.title()} İçin Namaz Vakitleri*\n\n"
            f"• *İmsak:* `{timings.get('Fajr')}`\n"
            f"• *Güneş:* `{timings.get('Sunrise')}`\n"
            f"• *Öğle:* `{timings.get('Dhuhr')}`\n"
            f"• *İkindi:* `{timings.get('Asr')}`\n"
            f"• *Akşam:* `{timings.get('Maghrib')}`\n"
            f"• *Yatsı:* `{timings.get('Isha')}`\n\n"
            f"⏰ _Ezan vakitlerine 10 dk kala otomatik hatırlatma yapılır._"
        )
        bot.reply_to(message, msg, parse_mode="Markdown")
    else:
        bot.reply_to(message, f"❌ '{city}' şehri için namaz vakitleri alınamadı. Lütfen şehir adını kontrol edin.")


@bot.message_handler(commands=['tarih'])
def handle_tarih(message):
    """
    /tarih komutu işleyicisi.
    """
    save_subscriber(message.chat.id)
    bot.reply_to(message, get_date_info(), parse_mode="Markdown")


@bot.message_handler(commands=['hava'])
def handle_hava(message):
    """
    /hava [şehir] komutu işleyicisi.
    """
    save_subscriber(message.chat.id)
    command_args = message.text.split(maxsplit=1)
    city = command_args[1].strip() if len(command_args) > 1 else DEFAULT_CITY

    w = get_weather(city)
    if w:
        msg = (
            f"🌤️ *{w['city']} İçin Hava Durumu*\n\n"
            f"🌡️ *Sıcaklık:* `{w['temp']}°C` (Hissedilen: `{w['feels']}°C`)\n"
            f"☁️ *Durum:* {w['desc']}\n"
            f"💧 *Nem:* `%{w['humidity']}`\n"
            f"💨 *Rüzgar Hızı:* `{w['wind']} km/s`"
        )
        bot.reply_to(message, msg, parse_mode="Markdown")
    else:
        bot.reply_to(message, f"❌ '{city}' için hava durumu bilgisi çekilemedi.")


@bot.message_handler(commands=['echo'])
def handle_echo(message):
    """
    /echo komutu işleyicisi.
    """
    save_subscriber(message.chat.id)
    command_args = message.text.split(maxsplit=1)
    if len(command_args) > 1:
        bot.reply_to(message, f"Söylediğin: {command_args[1]}")
    else:
        bot.reply_to(message, "⚠️ Lütfen yansıtmamı istediğiniz metni yazın.\n*Kullanım:* `/echo <mesajınız>`", parse_mode="Markdown")


@bot.message_handler(func=lambda message: message.text is not None)
def handle_general_chat(message):
    """
    Akıllı Mesaj Yakalama (NLP Intent Matcher) & Genel Sohbet
    """
    save_subscriber(message.chat.id)
    text = message.text.lower().strip()

    # Ezan / Namaz Soruları
    if any(word in text for word in ["ezan", "namaz", "vakit", "imsak", "iftar"]):
        # Şehir tespiti için mesajdan komut temizleme veya varsayılan şehir
        words = text.split()
        city = DEFAULT_CITY
        for w in words:
            if w not in ["ezan", "namaz", "vakit", "kaçta", "ne", "zaman", "bugün", "için"]:
                if len(w) > 2:
                    city = w
                    break
        timings = get_prayer_times(city)
        if timings:
            msg = (
                f"🕌 *{city.title()} İçin Namaz Vakitleri*\n\n"
                f"• *İmsak:* `{timings.get('Fajr')}`\n"
                f"• *Öğle:* `{timings.get('Dhuhr')}`\n"
                f"• *İkindi:* `{timings.get('Asr')}`\n"
                f"• *Akşam:* `{timings.get('Maghrib')}`\n"
                f"• *Yatsı:* `{timings.get('Isha')}`"
            )
            bot.reply_to(message, msg, parse_mode="Markdown")
            return

    # Tarih / Saat Soruları
    if any(phrase in text for phrase in ["tarih", "saat kaç", "bugün hangi gün", "günlerden ne"]):
        bot.reply_to(message, get_date_info(), parse_mode="Markdown")
        return

    # Hava Durumu Soruları
    if any(word in text for word in ["hava", "derece", "sıcaklık", "yağmur"]):
        words = text.split()
        city = DEFAULT_CITY
        for w in words:
            if w not in ["hava", "nasıl", "durumu", "kaç", "derece", "bugün", "için"]:
                if len(w) > 2:
                    city = w
                    break
        w_data = get_weather(city)
        if w_data:
            msg = (
                f"🌤️ *{w_data['city']} İçin Hava Durumu*\n\n"
                f"🌡️ *Sıcaklık:* `{w_data['temp']}°C` (Hissedilen: `{w_data['feels']}°C`)\n"
                f"☁️ *Durum:* {w_data['desc']}"
            )
            bot.reply_to(message, msg, parse_mode="Markdown")
            return

    # Selamlaşma & Sohbet
    if any(word in text for word in ["selam", "merhaba", "slm", "heydo"]):
        bot.reply_to(message, "Selam! Sana nasıl yardımcı olabilirim? 😊 Ezan vakitleri, hava durumu veya tarihi sorabilirsin.")
    elif "nasılsın" in text or "nasıl gidiyor" in text:
        bot.reply_to(message, "Harikayım! 🚀 Kırklareli ezan vakitlerini ve hava durumunu takip ediyorum. Sen nasılsın?")
    elif any(word in text for word in ["iyiyim", "süperim", "harikayım", "bomba"]):
        bot.reply_to(message, "Harika! Güzel bir gün geçirmeni dilerim 🌟")
    else:
        bot.reply_to(
            message,
            "Mesajını aldım! Kullanabileceğin komutları ve özellikleri öğrenmek için /help yazabilirsin. 💡"
        )


if __name__ == "__main__":
    print("🚀 BinaryForce Telegram Botu (Aşama 2) Başlatılıyor...")
    print("⏰ Kırklareli 10 Dakika Kala Ezan Hatırlatıcı Zamanlayıcısı Aktifleştiriliyor...")
    start_reminder_scheduler()
    print("Bot mesajları dinliyor... Durdurmak için Ctrl+C tuşlarına basın.")
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ Bot çalışırken bir hata oluştu: {e}")
