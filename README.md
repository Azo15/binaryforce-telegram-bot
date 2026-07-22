# BinaryForce Telegram Bot 🤖

BinaryForce Telegram Bot, **Python** ve **pyTelegramBotAPI** (`telebot`) kullanılarak geliştirilmiş, modüler, güvenli ve akıllı özelliklere sahip bir Telegram botudur.

---

## 📌 Gelişmiş Özellikler & Komutlar

- **🕌 Ezan Vakitleri (`/ezan [şehir]` veya `/vakit [şehir]`)**:
  - Aladhan API (Diyanet İşleri Başkanlığı metodu) kullanır.
  - Şehir belirtilmezse varsayılan olarak **Kırklareli** namaz vakitlerini (İmsak, Güneş, Öğle, İkindi, Akşam, Yatsı) listeler.
- **⏰ 10 Dakika Önce Ezan Hatırlatıcısı**:
  - Arka planda çalışan zamanlayıcı (Scheduler), **Kırklareli** ezan vakitlerine **10 dakika kala** kaydolan tüm kullanıcılara otomatik hatırlatma bildirimi gönderir.
- **📅 Tarih ve Gün Bilgisi (`/tarih`)**:
  - Güncel tarihi, Türkçe gün ismini (Örn: *21 Temmuz 2026, Salı*) ve anlık saati gösterir.
- **🌤️ Hava Durumu (`/hava [şehir]`)**:
  - wttr.in servisi üzerinden Türkçe anlık sıcaklık, hissedilen sıcaklık, nem oranı ve rüzgar hızını çeker (Varsayılan: **Kırklareli**).
- **🤖 Akıllı Mesaj Yakalama (Natural Language Matcher)**:
  - "ezan", "namaz kaçta", "bugün günlerden ne", "hava nasıl" gibi sohbet mesajlarını otomatik anlayarak doğrudan yanıt verir.

---

## 🛠️ Kurulum & Çalıştırma

### 1. Repoyu Klonlayın
```bash
git clone https://github.com/YOUR_USERNAME/binaryforce-telegram-bot.git
cd binaryforce-telegram-bot
```

### 2. Sanal Ortamı Aktifleştirin ve Bağımlılıkları Yükleyin
```bash
python -m venv venv
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 3. Çevre Değişkenlerini Yapılandırın (`.env`)
```env
BOT_TOKEN=8807117634:AAEq0U_eeFknijE8hgFMEmpALQ6JzS4Taus
```

### 4. Botu Çalıştırın
```bash
python main.py
```

---

## 🚀 Komut Kullanım Örnekleri

| Komut | Açıklama | Örnek Kullanım |
|---|---|---|
| `/start` | Botu başlatır ve bildirim listesine kaydeder. | `/start` |
| `/help` | Tüm komut ve detaylı kullanım menüsünü listeler. | `/help` |
| `/ezan [şehir]` | Namaz vakitlerini getirir (Varsayılan: Kırklareli). | `/ezan` veya `/ezan İstanbul` |
| `/tarih` | Güncel tarih, Türkçe gün ismi ve saati verir. | `/tarih` |
| `/hava [şehir]` | Anlık hava durumunu Türkçe raporlar. | `/hava Kırklareli` veya `/hava Ankara` |
| `/echo <metin>` | Gönderilen metni geri yansıtır. | `/echo BinaryForce` |
| Akıllı Sohbet | Doğal dildeki sorulara otomatik cevap verir. | `"kırklareli ezan"` veya `"bugün hava nasıl"` |

---

## 🎯 Conventional Commits Standartları

Proje geliştirme sürecinde aşağıdaki Git Commit mesajları kullanılmıştır:

- `feat: add prayer times (/ezan) command with Kirklareli default`
- `feat: implement 10-minute prayer reminder background scheduler`
- `feat: add date and dynamic day handler (/tarih)`
- `feat: add weather forecast module (/hava) using wttr.in API`
- `refactor: improve natural language intent matching and update /help`
- `docs: update README with new commands, reminders, and API guide`

---

## 📄 Lisans
Bu proje MIT Lisansı ile lisanslanmıştır.
