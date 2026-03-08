# 🚀 ULTIMATE CRYPTO BOT - UPGRADED VERSION

## ✨ YENİ ÖZELLİKLER

### 📊 Grafik Geliştirmeleri
- ✅ **İnteraktif Plotly Grafikler** - Zoom, pan, hover özellikli
- ✅ **Candlestick Chartlar** - EMA, RSI, MACD, Bollinger Bands
- ✅ **Portföy Performans Grafiği** - Kümülatif PnL takibi
- ✅ **Korelasyon Heatmap** - Coinler arası ilişki analizi
- ✅ **Telegram'a Otomatik Gönderim** - PNG formatında

### 🛡️ Risk Yönetimi
- ✅ **Otomatik Stop Loss** - ATR bazlı dinamik veya sabit %
- ✅ **Otomatik Take Profit** - Risk/Reward oranına göre
- ✅ **Position Sizing** - Kelly Criterion ile optimal boyutlandırma
- ✅ **Max Drawdown Kontrolü** - Otomatik trade durdurma
- ✅ **Eşzamanlı Trade Limiti** - Aşırı risk önleme
- ✅ **Trailing Stop** (Opsiyonel) - En yüksek fiyat takibi

### 💾 Veri Kalıcılığı
- ✅ **SQLite Database** - Tüm veriler kayıt altında
- ✅ **Pozisyon Geçmişi** - Her trade kaydedilir
- ✅ **Sinyal Arşivi** - Geçmiş sinyaller saklanır
- ✅ **Ayar Saklama** - Risk parametreleri kalıcı
- ✅ **Restart Sonrası Devam** - Bot kapansa bile veri kaybolmaz

### ⚡ Performans İyileştirmeleri
- ✅ **Cache Sistemi** - API çağrıları minimize edildi
- ✅ **Rate Limiting** - Binance ban önleme
- ✅ **Async Hazır Altyapı** - Gelecek için hazır

### 🎨 Telegram UI İyileştirmeleri
- ✅ **Ana Menü Klavyesi** - Hızlı erişim butonları
- ✅ **Inline Keyboards** - Coin seçimi için
- ✅ **Emoji & Formatlamalar** - Daha okunabilir mesajlar
- ✅ **Callback Handlers** - İnteraktif butonlar
- ✅ **Gelişmiş Komutlar** - Daha fazla kontrol

---

## 📦 KURULUM

### 1. Gerekli Kütüphaneleri Yükleyin

```bash
pip install -r requirements.txt --break-system-packages
```

Veya tek tek:
```bash
pip install ccxt pandas numpy scikit-learn matplotlib plotly kaleido pillow --break-system-packages
pip install pyTelegramBotAPI feedparser deep-translator schedule requests --break-system-packages
```

### 2. Telegram Bot Token'ınızı Ayarlayın

Kod içinde `TELEGRAM_TOKEN` ve `TELEGRAM_CHAT_ID` değerlerini kendi bilgilerinizle değiştirin:

```python
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID_HERE"
```

### 3. Botu Başlatın

```bash
python ultimate_bot_UPGRADED.py
```

---

## 🎮 KULLANIM

### 📱 Ana Menü Butonları

Bot başladığında Telegram'da şu butonlar görünür:

```
📊 Portföy    | 🎯 Sinyaller
📈 Grafikler  | 🤖 ML Tahmin
📰 Haberler   | ⚙️ Ayarlar
📋 Coin Listesi | ❓ Yardım
```

### 🔧 Temel Komutlar

#### Portföy Yönetimi
```
/portfolio veya /p      - Portföy durumu ve istatistikler
/stats                  - Detaylı performans analizi
/risk                   - Risk ayarlarını göster
/setrisk stop_loss 5    - Stop loss'u %5 yap
```

#### Sinyal & Analiz
```
/signals veya /s        - Son 1 saatteki sinyaller
/scan                   - Manuel sinyal taraması
/mlscan                 - ML tahmin taraması
/predict btc            - BTC için ML tahmini
```

#### Grafikler
```
/chart btc              - BTC candlestick grafiği
/correlation            - Korelasyon matrisi
```

#### Order Book & Market
```
/orderbook btc          - BTC order book analizi
/regime                 - Market regime (Trend/Range/Volatile)
/position btc           - BTC için optimal pozisyon boyutu (Kelly)
```

#### Backtest
```
/backtest btc           - 6 aylık backtest
/backtest eth 12        - 12 aylık backtest
```

#### Coin Yönetimi
```
/liste veya /list       - Takip edilen coinler
/ekle matic             - MATIC ekle
/sil matic              - MATIC çıkar
```

#### Haberler
```
/news                   - Manuel haber taraması
```

#### Diğer
```
/start veya /help       - Yardım menüsü
/report                 - Günlük rapor (manuel)
```

---

## ⚙️ RİSK AYARLARI

Bot başlangıçta şu risk parametreleriyle gelir:

```python
RISK_SETTINGS = {
    'max_position_size': 10,      # Maksimum pozisyon %10
    'max_drawdown': 20,           # Maksimum drawdown %20
    'default_stop_loss': 3,       # Default stop loss %3
    'default_take_profit': 6,     # Default take profit %6
    'max_concurrent_trades': 5,   # En fazla 5 eşzamanlı trade
    'risk_per_trade': 2           # Trade başına risk %2
}
```

### Ayarları Değiştirme

```bash
/setrisk stop_loss 5         # Stop loss'u %5 yap
/setrisk take_profit 10      # Take profit'i %10 yap
/setrisk max_position 15     # Max pozisyonu %15 yap
/setrisk max_drawdown 25     # Max drawdown'ı %25 yap
/setrisk risk_per_trade 3    # Trade başına riski %3 yap
/setrisk max_trades 3        # Max eşzamanlı trade'i 3 yap
```

---

## 🔄 OTOMATIK GÖREVLER

Bot arka planda şunları otomatik yapar:

| Görev | Sıklık | Açıklama |
|-------|--------|----------|
| ML Radar | 15 dakika | ML tahminleri tarar |
| Teknik Sinyal | 15 dakika | RSI, MACD, EMA sinyalleri |
| Haber Taraması | 10 dakika | RSS beslemelerinden haber |
| Korelasyon Analizi | 10 dakika | Coin korelasyonları |
| Market Regime | 30 dakika | Trend/Range/Volatile tespiti |
| Günlük Rapor | Her gün 20:00 | Performans özeti |
| Stop/Loss Kontrolü | 30 saniye | Aktif pozisyonları kontrol eder |

---

## 📊 GRAFİK ÖRNEKLERİ

### Candlestick Chart
- Mum grafiği (OHLC)
- EMA 20, 50, 200
- RSI (Oversold/Overbought seviyeleri)
- MACD histogram
- Volume bar chart
- Al/Sat sinyalleri işaretli

### Portfolio Chart
- Kümülatif PnL eğrisi
- Zaman bazlı performans
- İnteraktif zoom

### Correlation Heatmap
- 8x8 korelasyon matrisi
- Renkli kodlama (-1 kırmızı, +1 mavi)
- Değerler sayısal gösterilir

---

## 🛡️ STOP LOSS / TAKE PROFIT NASIL ÇALIŞIR?

### Otomatik Pozisyon Açma (Manuel veya Auto-Trade)

```python
# Örnek: BTC pozisyonu aç
PortfolioTracker.add_position(
    symbol='BTC/USDT',
    entry_price=50000,
    size=5.0,  # %5 pozisyon
    direction='long'
)
```

Bot otomatik olarak:
1. **Stop Loss** hesaplar (entry_price - %3)
2. **Take Profit** hesaplar (entry_price + %6)
3. Database'e kaydeder
4. Telegram'a bildirim gönderir

### Otomatik Kapanma

Bot her 30 saniyede bir aktif pozisyonları kontrol eder:

```python
PortfolioTracker.check_active_positions()
```

Eğer:
- Fiyat <= Stop Loss → Pozisyon kapatılır (STOP_LOSS)
- Fiyat >= Take Profit → Pozisyon kapatılır (TAKE_PROFIT)

Kapanma anında:
- Database'e kaydedilir
- PORTFOLIO_HISTORY'ye eklenir
- Telegram'a bildirim gönderilir

---

## 💾 DATABASE YAPISI

### Tablolar

#### `positions` - Pozisyon Geçmişi
```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY,
    symbol TEXT,
    entry_price REAL,
    entry_time TEXT,
    exit_price REAL,
    exit_time TEXT,
    size REAL,
    direction TEXT,
    pnl_pct REAL,
    stop_loss REAL,
    take_profit REAL,
    reason TEXT,
    status TEXT
)
```

#### `signals` - Sinyal Arşivi
```sql
CREATE TABLE signals (
    id INTEGER PRIMARY KEY,
    symbol TEXT,
    signal_type TEXT,
    price REAL,
    confidence REAL,
    timestamp TEXT,
    reason TEXT
)
```

#### `settings` - Ayarlar
```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
```

### Database Dosyası
- Konum: `crypto_bot.db`
- Format: SQLite3
- Boyut: Dinamik (trade sayısına göre)

---

## 🎯 ÖZELLİK KARŞILAŞTIRMA

| Özellik | Eski Kod | Upgrade |
|---------|----------|---------|
| **Grafikler** | Matplotlib (basit) | Plotly (interaktif) ✅ |
| **Grafik Gönderimi** | ❌ | PNG olarak Telegram'a ✅ |
| **Stop Loss** | Manuel | Otomatik ✅ |
| **Take Profit** | Manuel | Otomatik ✅ |
| **Veri Saklama** | Sadece RAM | SQLite Database ✅ |
| **Cache** | ❌ | 5 dk cache ✅ |
| **Telegram UI** | Basit text | Inline keyboard + butonlar ✅ |
| **Risk Yönetimi** | Basit | Kelly, Drawdown, Position sizing ✅ |
| **Dinamik Ayarlar** | ❌ | `/setrisk` komutu ✅ |
| **Portfolio Chart** | ❌ | Kümülatif PnL grafiği ✅ |
| **Correlation Chart** | ❌ | Heatmap ✅ |
| **Trailing Stop** | ❌ | Altyapı hazır (kullanılmıyor) ⚠️ |

---

## 🚦 İLK ÇALIŞTIRMADA NE OLUR?

1. ✅ Database oluşturulur (`crypto_bot.db`)
2. ✅ Korelasyon matrisi hesaplanır (8 coin için)
3. ✅ Market regime tespit edilir (BTC)
4. ✅ ML modelleri eğitilir (12 coin için, ~1 dakika)
5. ✅ Zamanlanmış görevler başlatılır
6. ✅ İlk taramalar yapılır:
   - Haber taraması
   - ML radar
   - Teknik sinyal taraması
7. ✅ Telegram dinlemesi aktif olur

---

## 🔧 GELİŞMİŞ KULLANIM

### Kelly Criterion ile Position Sizing

```bash
/position btc
```

Çıktı:
```
💼 POZİSYON BÜYÜKLÜĞÜ: BTC/USDT

📐 Kelly Criterion: 8.5%
✅ Önerilen (Kelly×0.5): 4.3%

📊 Win Rate: 62.5%
📈 Avg Win: +5.2%
📉 Avg Loss: -2.8%
🔢 Trade Sayısı: 24
```

### Market Regime Detection

```bash
/regime
```

Çıktı:
```
🌐 MARKET REGIME: BTC

📊 Mevcut: TRENDING
🎯 Güven: 78%

📈 Piyasa trend halinde. Trend takip stratejileri uygun.
```

### Order Book Analizi

```bash
/orderbook btc
```

Çıktı:
```
📊 ORDER BOOK: BTC/USDT

⚖️ Bid/Ask Ratio: 1.45
📈 Sentiment: BULLISH

🟢 ALIŞ DUVARLARI:
  $49850.00: 2.45 BTC
  $49800.00: 3.12 BTC

🔴 SATIŞ DUVARLARI:
  $50200.00: 1.89 BTC
  $50350.00: 2.67 BTC
```

---

## 📝 NOTLAR

### ⚠️ ÖNEMLİ UYARILAR

1. **Paper Trading**: Bot gerçek trade yapmaz, sadece sinyal verir
2. **Auto-Trade**: Sadece paper trading modunda çalışır (`/autotrade`)
3. **API Keys**: Gerçek trade için Binance API keys eklemeniz gerekir
4. **Risk**: Kripto piyasası volatildir, risk yönetimi çok önemlidir

### 🐛 HATA GİDERME

**Grafik oluşmuyor:**
```bash
pip install kaleido pillow --break-system-packages
```

**Threading hatası:**
```python
matplotlib.use('Agg')  # Zaten kodda var
```

**Telegram gönderemiyorum:**
- Token'ı kontrol edin
- Chat ID'yi kontrol edin
- Bot'u Telegram'da `/start` ile başlatın

**Database hatası:**
```bash
# Database'i sıfırla
rm crypto_bot.db
# Bot tekrar başlatılınca yeniden oluşur
```

---

## 🎉 SONUÇ

**Upgrade edilen bot artık:**

✅ Profesyonel grafikler üretir (Plotly)
✅ Otomatik stop loss ve take profit yönetir
✅ Tüm verileri database'de saklar
✅ Daha hızlı çalışır (cache sayesinde)
✅ Daha kullanıcı dostu arayüze sahip (Telegram UI)
✅ Gelişmiş risk yönetimi yapar (Kelly, Drawdown)
✅ Daha fazla analiz sunar (correlation, regime, orderbook)

**Kullanmaya başlamak için:**

```bash
python ultimate_bot_UPGRADED.py
```

**Telegram'da `/start` yazın ve botunuzun keyfini çıkarın! 🚀**

---

## 📧 DESTEK

Sorun yaşarsanız log dosyasını kontrol edin:
```bash
tail -f ultimate_bot.log
```

---

**Yapım: Ultimate Crypto Bot Upgraded Version**
**Tarih: 2024**
**Versiyon: 2.0**
