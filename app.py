import sys
import io
import streamlit as st
import threading
import os

# Streamlit UI Setup
st.set_page_config(page_title="KriptoGraf Finans Botu", page_icon="📈")
st.title("📈 KriptoGraf Finans Botu")

st.info("Bot sistemi başlatılıyor... Lütfen bekleyin.")

# 1. WINDOWS TERMINAL HATASINI SADECE WINDOWS'TA ÇÖZELİM
if os.name == 'nt' and sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import matplotlib
matplotlib.use('Agg') 

import ccxt
import pandas as pd
import numpy as np
import requests
import time
import telebot
from telebot import types
import feedparser
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
import plotly.express as px
import logging
import schedule
import warnings
from threading import Thread
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator
from collections import deque
import json
import sqlite3
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import os
import tempfile
from contextlib import contextmanager
from google import genai

warnings.filterwarnings('ignore')

# ==========================================
# LOGLAMA (UTF-8 DESTEKLİ)
# ==========================================
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('ultimate_bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ==========================================
# AYARLAR
# ==========================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8272358639:AAHIgBHaFT5pZ6oiJyBDLUhgbnyXcIoVl58")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "-1003729347227")
TELEGRAM_CHANNEL_LINK = os.environ.get("TELEGRAM_CHANNEL_LINK", "https://t.me/kriptoograf")
LINKTREE_LINK = os.environ.get("LINKTREE_LINK", "https://linktr.ee/KriptoGraf")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCSTuuqxCSXaiNRanacZ9J5BxkLWZQ-Hg4")
VIP_USER_ID = os.environ.get("VIP_USER_ID", "718632638")
GITHUB_ACTIONS = os.environ.get("GITHUB_ACTIONS", "false").lower() == "true"
RUN_ONCE = os.environ.get("RUN_ONCE", "false").lower() == "true"
IS_CI_MODE = GITHUB_ACTIONS or RUN_ONCE

# Servisleri başlat
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
    GEN_MODEL = 'gemini-1.5-flash'
    logger.info("✅ Gemini AI başlatıldı")
except Exception as e:
    logger.error(f"❌ Gemini hatası: {e}")
    client = None

try:
    bot = telebot.TeleBot(TELEGRAM_TOKEN)
    logger.info("✅ Telegram bot nesnesi oluşturuldu")
except Exception as e:
    logger.error(f"❌ Bot hatası: {e}")
    bot = None

exchange = None

def init_all_services():
    """Ağır yükleme gerektiren servisleri arka planda başlatır"""
    global exchange
    if exchange is None:
        try:
            exchange = initialize_exchange()
            return True
        except Exception as e:
            logger.error(f"❌ Borsa bağlantı hatası: {e}")
            return False
    return True

# Trading
# Başlangıçta boş listeler, daha sonra update_symbols() ile dolar bazında hacmi yüksek tüm coinler yüklenecek.
SYMBOLS = []
TIMEFRAMES = ['15m', '1h', '4h', '1d']
MAIN_TIMEFRAME = '15m'
VOL_SPIKE_LIMIT = 2.5

# Risk Management
RISK_SETTINGS = {

    'max_position_size': 10,       # %
    'max_concurrent_trades': 5,
    'risk_per_trade': 1,           # %
    'max_drawdown': 20,            # %
    'default_stop_loss': 3,        # %
    'default_take_profit': 6,      # %
}

# VIP Raporu için kullanıcı ID (Özel mesaj için)
VIP_USER_ID = "718632638" 
VIP_SYMBOLS = ['BTC/USDT', 'XRP/USDT', 'BNB/USDT', 'AVAX/USDT', 'SOL/USDT']


# Data Storage
SIGNAL_HISTORY = []
ACTIVE_POSITIONS = {}
PORTFOLIO_HISTORY = []
USER_STATS = {}
BACKTEST_RESULTS = {}
CORRELATION_DATA = {}
ML_MODELS = {}
MARKET_REGIME = {'current': 'UNKNOWN', 'confidence': 0}
CACHE = {}  # Performance cache

# Paylaşımlı Exchange Instance (Singleton)
# Paylaşımlı Exchange Instance (Singleton)
def initialize_exchange():
    """MEXC borsasını kullanarak bağlantı kurar (Kısıtlamaları aşmak için en iyi alternatif)"""
    try:
        logger.info("📡 MEXC borsasına bağlanılıyor...")
        ex = ccxt.mexc({
            'enableRateLimit': True, 
            'timeout': 30000,
            'options': {
                'defaultType': 'spot'
            }
        })
        ex.load_markets()
        logger.info("✅ MEXC borsasına başarıyla bağlanıldı!")
        return ex
    except Exception as e:
        logger.error(f"❌ MEXC bağlantısı başarısız: {e}")
        # Hata durumunda bile MEXC dönelim
        return ccxt.mexc({'enableRateLimit': True})

try:
    exchange = initialize_exchange()
except Exception as e:
    logger.error(f"❌ Exchange başlatılamadı: {e}")
    exchange = ccxt.mexc({'enableRateLimit': True})

MANUAL_PORTFOLIO = {}  # {'BTC/USDT': {'amount': 0.5, 'cost': 45000, 'date': ...}}

# Haber Sentiment Analizi bölümü iptal edildi, sadece Teknik Analiz.

# ==========================================
# TÜM COİNLERİ TARAMA YAPISI (YENİ!)
# ==========================================
def update_symbols():
    """MEXC üzerindeki USDT çiftlerini hacme göre günceller"""
    global SYMBOLS
    try:
        logger.info("🔄 MEXC piyasaları güncelleniyor...")
        markets = exchange.load_markets()
        
        valid_symbols = []
        for symbol, market in markets.items():
            # Sadece USDT bazlı spot marketleri filtreleniyor
            if market.get('active', True) and symbol.endswith('/USDT') and market.get('type') == 'spot':
                base_coin = symbol.split('/')[0]
                # Stabil coinleri ele
                if base_coin not in ['USDT', 'USDC', 'DAI', 'BUSD', 'EUR']:
                    valid_symbols.append(symbol)
                
        # API'den ticker verilerini alıp hacim filtresi uygula
        tickers = exchange.fetch_tickers(valid_symbols)
        
        filtered_symbols = []
        for symbol, data in tickers.items():
            # quoteVolume: 24 saatlik işlem hacmi
            if data.get('quoteVolume') and data['quoteVolume'] > 200000: # MEXC için 200k hacim yeterli
                filtered_symbols.append(symbol)
                
        # Hacme göre sırala ve en iyi 50'yi al
        filtered_symbols.sort(key=lambda s: tickers[s].get('quoteVolume', 0), reverse=True)
        SYMBOLS = filtered_symbols[:50]
        logger.info(f"✅ MEXC üzerinde {len(SYMBOLS)} aktif coin hazır.")
    except Exception as e:
        logger.error(f"❌ Piyasaları güncellerken hata oluştu: {e}")
        if not SYMBOLS:
            SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'AVAX/USDT']

# ==========================================
# DATABASE (YENİ!)
# ==========================================
class Database:
    """SQLite ile kalıcı veri saklama"""
    
    @staticmethod
    @contextmanager
    def get_connection():
        """Thread-safe veritabanı bağlantısı"""
        conn = sqlite3.connect('crypto_bot.db')
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def init_db():
        """Veritabanını başlat"""
        with Database.get_connection() as conn:
            c = conn.cursor()
            
            c.execute('''CREATE TABLE IF NOT EXISTS positions
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                          status TEXT)''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS signals
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          symbol TEXT,
                          signal_type TEXT,
                          price REAL,
                          confidence REAL,
                          timestamp TEXT,
                          reason TEXT)''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS settings
                         (key TEXT PRIMARY KEY,
                          value TEXT)''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS manual_portfolio
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          symbol TEXT,
                          amount REAL,
                          avg_price REAL,
                          timestamp TEXT)''')
        
        logger.info("✅ Database initialized")
    
    @staticmethod
    def save_position(pos_data):
        """Pozisyon kaydet"""
        with Database.get_connection() as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO positions 
                         (symbol, entry_price, entry_time, exit_price, exit_time, 
                          size, direction, pnl_pct, stop_loss, take_profit, reason, status)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (pos_data.get('symbol'), pos_data.get('entry_price'), 
                       pos_data.get('entry_time'), pos_data.get('exit_price'),
                       pos_data.get('exit_time'), pos_data.get('size'),
                       pos_data.get('direction'), pos_data.get('pnl_pct'),
                       pos_data.get('stop_loss'), pos_data.get('take_profit'),
                       pos_data.get('reason'), pos_data.get('status')))
    
    @staticmethod
    def save_signal(signal_data):
        """Sinyal kaydet"""
        with Database.get_connection() as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO signals 
                         (symbol, signal_type, price, confidence, timestamp, reason)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (signal_data.get('symbol'), signal_data.get('type'),
                       signal_data.get('price'), signal_data.get('confidence'),
                       signal_data.get('timestamp'), signal_data.get('reason')))
    
    @staticmethod
    def load_positions(status='OPEN'):
        """Pozisyonları yükle"""
        with Database.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM positions WHERE status=?', (status,))
            return c.fetchall()
    
    @staticmethod
    def get_setting(key, default=None):
        """Ayar getir"""
        with Database.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT value FROM settings WHERE key=?', (key,))
            row = c.fetchone()
            return row[0] if row else default
    
    @staticmethod
    def set_setting(key, value):
        """Ayar kaydet"""
        with Database.get_connection() as conn:
            c = conn.cursor()
            c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                      (key, str(value)))
    
    @staticmethod
    def get_recent_signals(limit=50):
        """Geçmiş sinyalleri getir"""
        try:
            with Database.get_connection() as conn:
                c = conn.cursor()
                c.execute('SELECT symbol, signal_type, price, confidence, reason, timestamp FROM signals ORDER BY id DESC LIMIT ?', (limit,))
                rows = c.fetchall()
                # Listeyi ters çevir (eskiden yeniye) ki append ile uyumlu olsun
                return [{'symbol': r[0], 'type': r[1], 'price': r[2], 'confidence': r[3], 'reason': r[4], 'timestamp': r[5]} for r in rows][::-1]
        except Exception as e:
            logger.error(f"Sinyal geçmişi yüklenemedi: {e}")
            return []

# ==========================================
# CACHE MANAGER (YENİ!)
# ==========================================
    @staticmethod
    def add_manual_position(symbol, amount, avg_price):
        """Manuel pozisyon ekle"""
        with Database.get_connection() as conn:
            c = conn.cursor()
            c.execute('INSERT INTO manual_portfolio (symbol, amount, avg_price, timestamp) VALUES (?, ?, ?, ?)',
                      (symbol, amount, avg_price, datetime.now()))
    
    @staticmethod
    def get_manual_positions():
        """Manuel pozisyonları getir"""
        try:
            with Database.get_connection() as conn:
                c = conn.cursor()
                c.execute('SELECT symbol, amount, avg_price FROM manual_portfolio')
                rows = c.fetchall()
                positions = {}
                for r in rows:
                    sym = r[0]
                    if sym not in positions:
                        positions[sym] = {'amount': 0, 'cost': 0}
                    
                    positions[sym]['amount'] += r[1]
                    positions[sym]['cost'] += (r[1] * r[2])
                
                final_pos = []
                for sym, data in positions.items():
                    if data['amount'] > 0:
                        avg_price = data['cost'] / data['amount']
                        final_pos.append({'symbol': sym, 'amount': data['amount'], 'avg_price': avg_price})
                
                return final_pos
        except:
            return []

    @staticmethod
    def delete_manual_position(symbol):
        """Manuel pozisyon sil"""
        with Database.get_connection() as conn:
            c = conn.cursor()
            c.execute('DELETE FROM manual_portfolio WHERE symbol=?', (symbol,))

# ==========================================
# CACHE MANAGER (YENİ!)
# ==========================================
class CacheManager:
    """Performans için cache yönetimi"""
    
    @staticmethod
    def get(key, max_age=300):
        """Cache'den veri al (5 dk default)"""
        if key not in CACHE:
            return None
        
        cached_time, cached_data = CACHE[key]
        if time.time() - cached_time > max_age:
            del CACHE[key]
            return None
        
        return cached_data
    
    @staticmethod
    def set(key, data):
        """Cache'e veri kaydet"""
        CACHE[key] = (time.time(), data)
    
    @staticmethod
    def clear():
        """Cache'i temizle"""
        CACHE.clear()

# ==========================================
# RATE LIMITING
# ==========================================
class RateLimiter:
    def __init__(self, max_calls, time_window):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = deque()
    
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            now = time.time()
            while self.calls and self.calls[0] < now - self.time_window:
                self.calls.popleft()
            
            if len(self.calls) >= self.max_calls:
                sleep_time = self.time_window - (now - self.calls[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    self.calls.clear()
            
            self.calls.append(time.time())
            return func(*args, **kwargs)
        return wrapper

binance_limiter = RateLimiter(max_calls=8, time_window=60)

# ==========================================
# RISK MANAGER (YENİ - GELIŞTIRILMIŞ!)
# ==========================================
class RiskManager:
    """Gelişmiş risk yönetimi"""
    
    @staticmethod
    def calculate_stop_loss(entry_price, direction, atr, multiplier=2.0):
        """ATR bazlı dinamik stop loss hesapla"""
        if direction == 'LONG':
            stop_loss = entry_price - (atr * multiplier)
        else:
            stop_loss = entry_price + (atr * multiplier)
        return stop_loss

    @staticmethod
    def calculate_position_size(symbol, account_balance, risk_pct=None):
        """Pozisyon büyüklüğünü hesapla"""
        if risk_pct is None:
            risk_pct = RISK_SETTINGS['risk_per_trade']
        
        # Maksimum eşzamanlı trade kontrolü
        if len(ACTIVE_POSITIONS) >= RISK_SETTINGS['max_concurrent_trades']:
            return 0
        
        # Kelly criterion ile optimize et
        kelly_data = PositionSizer.calculate_kelly(symbol)
        if 'recommended' in kelly_data:
            optimal_size = kelly_data['recommended']
        else:
            optimal_size = risk_pct
        
        # Maximum position size kontrolü
        max_size = RISK_SETTINGS['max_position_size']
        position_size = min(optimal_size, max_size)
        
        return position_size
    
    @staticmethod
    def calculate_stop_loss(entry_price, direction='long', atr=None):
        """Stop loss hesapla"""
        if atr:
            # ATR bazlı dinamik stop loss
            if direction == 'long':
                stop_loss = entry_price - (2 * atr)
            else:
                stop_loss = entry_price + (2 * atr)
        else:
            # Sabit yüzde
            stop_pct = RISK_SETTINGS['default_stop_loss'] / 100
            if direction == 'long':
                stop_loss = entry_price * (1 - stop_pct)
            else:
                stop_loss = entry_price * (1 + stop_pct)
        
        return stop_loss
    
    @staticmethod
    def calculate_take_profit(entry_price, direction='long', risk_reward=2):
        """Take profit hesapla"""
        tp_pct = RISK_SETTINGS['default_take_profit'] / 100
        
        if direction == 'long':
            take_profit = entry_price * (1 + tp_pct)
        else:
            take_profit = entry_price * (1 - tp_pct)
        
        return take_profit
    
    @staticmethod
    def check_drawdown():
        """Maksimum drawdown kontrolü"""
        if not PORTFOLIO_HISTORY:
            return True
        
        df = pd.DataFrame(PORTFOLIO_HISTORY)
        cumulative_pnl = df['pnl_pct'].sum()
        
        if cumulative_pnl < -RISK_SETTINGS['max_drawdown']:
            logger.warning(f"⚠️ MAX DRAWDOWN AŞILDI: {cumulative_pnl:.2f}%")
            return False
        
        return True
    
    @staticmethod
    def can_trade():
        """Trade yapılabilir mi?"""
        # Drawdown kontrolü
        if not RiskManager.check_drawdown():
            return False, "Max drawdown aşıldı"
        
        # Eşzamanlı trade kontrolü
        if len(ACTIVE_POSITIONS) >= RISK_SETTINGS['max_concurrent_trades']:
            return False, f"Max {RISK_SETTINGS['max_concurrent_trades']} trade limitine ulaşıldı"
        
        return True, "OK"

# ==========================================
# GÜVENLI TELEGRAM MESAJ GÖNDERİCİ
# ==========================================
def safe_send_message(chat_id, text, parse_mode="Markdown", **kwargs):
    """Telegram mesajını güvenli şekilde gönder. Markdown hatası olursa düz metin olarak dener."""
    try:
        bot.send_message(chat_id, text, parse_mode=parse_mode, **kwargs)
    except Exception as e:
        try:
            # Markdown parse hatası - düz metin olarak gönder
            bot.send_message(chat_id, text, **kwargs)
        except Exception as e2:
            logger.error(f"Telegram mesaj hatası: {e2}")

# ==========================================
# CHART GENERATOR (YENİ!)
# ==========================================
class ChartGenerator:
    """Plotly ile profesyonel grafikler"""
    
    @staticmethod
    def create_candlestick_chart(symbol, df, signals=None):
        """ULTRA PROFESYONEL GRAFİK"""
        try:
            # 4 panel
            fig = make_subplots(
                rows=4, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.02,
                row_heights=[0.5, 0.2, 0.15, 0.15],
                subplot_titles=(f'{symbol} - Teknik Analiz', 'Volume', 'RSI+Stoch', 'MACD')
            )
            
            # Panel 1: Candlestick + EMA + BB + VWAP + Destek/Direnç + Fibonacci
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['open'], high=df['high'], 
                low=df['low'], close=df['close'], name='Fiyat',
                increasing_line_color='#00ff88', decreasing_line_color='#ff3860'
            ), row=1, col=1)
            
            # EMA'lar
            fig.add_trace(go.Scatter(x=df.index, y=df['ema_20'], name='EMA 20', 
                                    line=dict(color='#ffa500', width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['ema_50'], name='EMA 50',
                                    line=dict(color='#00bfff', width=1.5)), row=1, col=1)
            
            # Bollinger Bands
            fig.add_trace(go.Scatter(x=df.index, y=df['bb_upper'], name='BB',
                                    line=dict(color='#9370db', dash='dot')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['bb_lower'], 
                                    line=dict(color='#9370db', dash='dot'),
                                    fill='tonexty', fillcolor='rgba(147,112,219,0.1)'), row=1, col=1)
            
            # VWAP
            if 'vwap' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['vwap'], name='VWAP',
                                        line=dict(color='#ffff00', dash='dash')), row=1, col=1)
            
            # Destek/Direnç otomatik
            recent = df[-50:]
            highs = [recent['high'].iloc[i] for i in range(5, len(recent)-5) 
                    if all(recent['high'].iloc[i] >= recent['high'].iloc[i-5:i+6])]
            lows = [recent['low'].iloc[i] for i in range(5, len(recent)-5)
                   if all(recent['low'].iloc[i] <= recent['low'].iloc[i-5:i+6])]
            
            for level in sorted(set(highs), reverse=True)[:3]:
                fig.add_hline(y=level, line_dash="dash", line_color="#ff3860", row=1, col=1)
            for level in sorted(set(lows))[:3]:
                fig.add_hline(y=level, line_dash="dash", line_color="#00ff88", row=1, col=1)
            
            # Fibonacci
            high = df['high'].tail(100).max()
            low = df['low'].tail(100).min()
            diff = high - low
            for level, color in [(0.236, '#ff6b6b'), (0.382, '#ffa500'), (0.5, '#ffff00'), (0.618, '#00ff88')]:
                fig.add_hline(y=high - level*diff, line_dash="dot", 
                             line_color=color, opacity=0.3, row=1, col=1)
            
            # Panel 2: Volume
            colors = ['#ff3860' if df['close'].iloc[i] < df['open'].iloc[i] else '#00ff88' 
                     for i in range(len(df))]
            fig.add_trace(go.Bar(x=df.index, y=df['volume'], marker_color=colors), row=2, col=1)
            
            # Panel 3: RSI + Stochastic
            fig.add_trace(go.Scatter(x=df.index, y=df['rsi'], name='RSI',
                                    line=dict(color='#00ffff', width=2)), row=3, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="#ff3860", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="#00ff88", row=3, col=1)
            
            if 'stoch_k' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['stoch_k'], name='Stoch',
                                        line=dict(color='#ffa500')), row=3, col=1)
            
            # Panel 4: MACD
            fig.add_trace(go.Scatter(x=df.index, y=df['macd'], name='MACD',
                                    line=dict(color='#00ff88', width=2)), row=4, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['signal'], name='Signal',
                                    line=dict(color='#ff3860', width=2)), row=4, col=1)
            
            hist_colors = ['#00ff88' if v >= 0 else '#ff3860' for v in df['macd_hist']]
            fig.add_trace(go.Bar(x=df.index, y=df['macd_hist'], 
                                marker_color=hist_colors, opacity=0.5), row=4, col=1)
            
            # Layout
            fig.update_layout(
                title=f'{symbol} - Ultra Profesyonel Analiz',
                xaxis_rangeslider_visible=False,
                height=1200,
                template='plotly_dark',
                plot_bgcolor='#0d0f14',
                paper_bgcolor='#0d0f14',
                font=dict(color='#ffffff')
            )
            
            fig.update_xaxes(gridcolor='#2a2e39')
            fig.update_yaxes(gridcolor='#2a2e39')
            
            # Kaydet
            temp_dir = tempfile.gettempdir()
            filename = os.path.join(temp_dir, f'chart_{symbol.replace("/", "_")}.png')
            pio.write_image(fig, filename, width=1400, height=1200, scale=2)
            
            return filename
            
        except Exception as e:
            logger.error(f"Grafik hatası: {e}")
            return None
    
    @staticmethod
    def create_portfolio_chart():
        """Portföy performans grafiği"""
        try:
            if not PORTFOLIO_HISTORY:
                return None
            
            df = pd.DataFrame(PORTFOLIO_HISTORY)
            df['cumulative_pnl'] = df['pnl_pct'].cumsum()
            
            fig = go.Figure()
            
            # Kümülatif PnL
            fig.add_trace(
                go.Scatter(
                    x=df['time'],
                    y=df['cumulative_pnl'],
                    mode='lines',
                    name='Cumulative PnL',
                    line=dict(color='cyan', width=2),
                    fill='tozeroy'
                )
            )
            
            # Sıfır çizgisi
            fig.add_hline(y=0, line_dash="dash", line_color="white")
            
            fig.update_layout(
                title='Portfolio Performance',
                xaxis_title='Time',
                yaxis_title='Cumulative PnL (%)',
                template='plotly_dark',
                height=500
            )
            
            temp_dir = tempfile.gettempdir()
            filename = os.path.join(temp_dir, f'portfolio_{int(time.time())}.png')
            pio.write_image(fig, filename, width=1200, height=600)
            
            return filename
            
        except Exception as e:
            logger.error(f"Portfolio chart hatası: {e}")
            return None
    
    @staticmethod
    def create_correlation_heatmap():
        """Korelasyon heatmap"""
        try:
            if not CORRELATION_DATA:
                return None
            
            corr_matrix = CORRELATION_DATA.get('matrix')
            if corr_matrix is None:
                return None
            
            fig = go.Figure(data=go.Heatmap(
                z=corr_matrix.values,
                x=corr_matrix.columns,
                y=corr_matrix.columns,
                colorscale='RdBu',
                zmid=0,
                text=np.round(corr_matrix.values, 2),
                texttemplate='%{text}',
                textfont={"size": 10}
            ))
            
            fig.update_layout(
                title='Coin Correlation Matrix',
                template='plotly_dark',
                height=700,
                width=700
            )
            
            temp_dir = tempfile.gettempdir()
            filename = os.path.join(temp_dir, f'correlation_{int(time.time())}.png')
            pio.write_image(fig, filename, width=1000, height=1000)
            
            return filename
            
        except Exception as e:
            logger.error(f"Correlation chart hatası: {e}")
            return None

    @staticmethod
    def create_market_heatmap(symbols_data):
        """Kripto Heatmap (Treemap)"""
        try:
            df = pd.DataFrame(symbols_data)
            if df.empty:
                return None
            
            # Treemap için figür oluştur
            fig = px.treemap(
                df, 
                path=[px.Constant("Market"), 'symbol'], 
                values='volume',
                color='change',
                color_continuous_scale='RdYlGn',
                range_color=[-10, 10],  # %10 ve -%10 arası renk skalası
                hover_data=['price', 'change', 'volume'],
                title='Crypto Market Heatmap (By Volume & 24h Change)'
            )
            
            fig.update_layout(
                template='plotly_dark',
                paper_bgcolor='#0d0f14',
                font=dict(color='#ffffff')
            )
            
            temp_dir = tempfile.gettempdir()
            filename = os.path.join(temp_dir, f'heatmap_{int(time.time())}.png')
            pio.write_image(fig, filename, width=1200, height=800)
            
            return filename
        except Exception as e:
            logger.error(f"Heatmap hatası: {e}")
            return None

# ==========================================
# PORTFOLIO TRACKER (GELIŞTIRILMIŞ!)
# ==========================================
class PortfolioTracker:
    """Gelişmiş portföy takibi"""
    
    @staticmethod
    def add_position(symbol, entry_price, size, direction='long', stop_loss=None, take_profit=None):
        """Yeni pozisyon ekle"""
        # Stop loss ve take profit hesapla
        if stop_loss is None:
            stop_loss = RiskManager.calculate_stop_loss(entry_price, direction)
        if take_profit is None:
            take_profit = RiskManager.calculate_take_profit(entry_price, direction)
        
        ACTIVE_POSITIONS[symbol] = {
            'entry_price': entry_price,
            'entry_time': datetime.now(),
            'size': size,
            'direction': direction,
            'status': 'OPEN',
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'highest_price': entry_price if direction == 'long' else entry_price,
            'lowest_price': entry_price if direction == 'short' else entry_price
        }
        
        # Database'e kaydet
        Database.save_position({
            'symbol': symbol,
            'entry_price': entry_price,
            'entry_time': str(datetime.now()),
            'exit_price': None,
            'exit_time': None,
            'size': size,
            'direction': direction,
            'pnl_pct': 0,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'reason': 'ENTRY',
            'status': 'OPEN'
        })
        
        logger.info(f"📊 Pozisyon açıldı: {symbol} @ ${entry_price:.2f}")
        logger.info(f"   🛑 Stop Loss: ${stop_loss:.2f}")
        logger.info(f"   🎯 Take Profit: ${take_profit:.2f}")
        
        # Telegram bildirimi
        msg = f"🟢 **YENİ POZİSYON**\n\n"
        msg += f"💎 {symbol}\n"
        msg += f"📍 Giriş: ${entry_price:.2f}\n"
        msg += f"📊 Büyüklük: {size:.2f}%\n"
        msg += f"📈 Yön: {direction.upper()}\n"
        msg += f"🛑 Stop Loss: ${stop_loss:.2f} ({((stop_loss-entry_price)/entry_price*100):.2f}%)\n"
        msg += f"🎯 Take Profit: ${take_profit:.2f} ({((take_profit-entry_price)/entry_price*100):.2f}%)\n"
        
        safe_send_message(TELEGRAM_CHAT_ID, msg)
    
    @staticmethod
    def close_position(symbol, exit_price, reason='MANUAL'):
        """Pozisyon kapat"""
        if symbol not in ACTIVE_POSITIONS:
            return None
        
        pos = ACTIVE_POSITIONS[symbol]
        entry = pos['entry_price']
        
        if pos['direction'] == 'long':
            pnl_pct = ((exit_price - entry) / entry) * 100
        else:
            pnl_pct = ((entry - exit_price) / entry) * 100
        
        result = {
            'symbol': symbol,
            'entry': entry,
            'exit': exit_price,
            'pnl_pct': pnl_pct,
            'duration': (datetime.now() - pos['entry_time']).total_seconds() / 3600,
            'reason': reason,
            'time': datetime.now(),
            'stop_loss': pos.get('stop_loss'),
            'take_profit': pos.get('take_profit')
        }
        
        PORTFOLIO_HISTORY.append(result)
        
        # Database'e kaydet
        Database.save_position({
            'symbol': symbol,
            'entry_price': entry,
            'entry_time': str(pos['entry_time']),
            'exit_price': exit_price,
            'exit_time': str(datetime.now()),
            'size': pos['size'],
            'direction': pos['direction'],
            'pnl_pct': pnl_pct,
            'stop_loss': pos.get('stop_loss'),
            'take_profit': pos.get('take_profit'),
            'reason': reason,
            'status': 'CLOSED'
        })
        
        del ACTIVE_POSITIONS[symbol]
        
        logger.info(f"{'✅' if pnl_pct > 0 else '❌'} Pozisyon kapandı: {symbol} | PnL: {pnl_pct:+.2f}% | Sebep: {reason}")
        
        # Telegram bildirimi
        emoji = '🟢' if pnl_pct > 0 else '🔴'
        msg = f"{emoji} **POZİSYON KAPANDI**\n\n"
        msg += f"💎 {symbol}\n"
        msg += f"📍 Giriş: ${entry:.2f}\n"
        msg += f"📍 Çıkış: ${exit_price:.2f}\n"
        msg += f"💰 PnL: **{pnl_pct:+.2f}%**\n"
        msg += f"⏱️ Süre: {result['duration']:.1f} saat\n"
        msg += f"📝 Sebep: {reason}\n"
        
        safe_send_message(TELEGRAM_CHAT_ID, msg)
        
        return result
    
    @staticmethod
    def check_active_positions():
        """Aktif pozisyonları kontrol et - Stop Loss / Take Profit"""
        for symbol, pos in list(ACTIVE_POSITIONS.items()):
            try:
                # Cache kontrolü
                cache_key = f"price_{symbol}"
                ticker = CacheManager.get(cache_key, max_age=30)
                
                if ticker is None:
                    ticker = exchange.fetch_ticker(symbol)
                    CacheManager.set(cache_key, ticker)
                
                current_price = ticker['last']
                entry = pos['entry_price']
                direction = pos['direction']
                
                # PnL hesapla
                if direction == 'long':
                    pnl_pct = ((current_price - entry) / entry) * 100
                else:
                    pnl_pct = ((entry - current_price) / entry) * 100
                
                pos['current_price'] = current_price
                pos['pnl_pct'] = pnl_pct
                
                # En yüksek/düşük fiyat takibi (trailing stop için)
                if direction == 'long':
                    if current_price > pos['highest_price']:
                        pos['highest_price'] = current_price
                else:
                    if current_price < pos['lowest_price']:
                        pos['lowest_price'] = current_price
                
                # Trailing Stop Loss (%3 geri çekilme)
                trailing_pct = 0.03
                sl_val = pos.get('stop_loss', 0)
                if direction == 'long' and pos['highest_price'] > entry:
                    trailing_stop = pos['highest_price'] * (1 - trailing_pct)
                    if current_price <= trailing_stop and (sl_val is None or trailing_stop > sl_val):
                        PortfolioTracker.close_position(symbol, current_price, 'TRAILING_STOP')
                        logger.warning(f"🚨 Trailing Stop tetiklendi: {symbol} (En yüksek: ${pos['highest_price']:.2f})")
                        continue
                elif direction == 'short' and pos['lowest_price'] < entry:
                    trailing_stop = pos['lowest_price'] * (1 + trailing_pct)
                    if current_price >= trailing_stop and (sl_val is None or trailing_stop < sl_val):
                        PortfolioTracker.close_position(symbol, current_price, 'TRAILING_STOP')
                        logger.warning(f"🚨 Trailing Stop tetiklendi: {symbol} (En düşük: ${pos['lowest_price']:.2f})")
                        continue
                
                # Stop Loss kontrolü
                stop_loss = pos.get('stop_loss')
                if stop_loss:
                    if direction == 'long' and current_price <= stop_loss:
                        PortfolioTracker.close_position(symbol, current_price, 'STOP_LOSS')
                        logger.warning(f"🛑 Stop Loss tetiklendi: {symbol}")
                        continue
                    elif direction == 'short' and current_price >= stop_loss:
                        PortfolioTracker.close_position(symbol, current_price, 'STOP_LOSS')
                        logger.warning(f"🛑 Stop Loss tetiklendi: {symbol}")
                        continue
                
                # Take Profit kontrolü
                take_profit = pos.get('take_profit')
                if take_profit:
                    if direction == 'long' and current_price >= take_profit:
                        PortfolioTracker.close_position(symbol, current_price, 'TAKE_PROFIT')
                        logger.info(f"🎯 Take Profit tetiklendi: {symbol}")
                        continue
                    elif direction == 'short' and current_price <= take_profit:
                        PortfolioTracker.close_position(symbol, current_price, 'TAKE_PROFIT')
                        logger.info(f"🎯 Take Profit tetiklendi: {symbol}")
                        continue
                
            except Exception as e:
                logger.error(f"Pozisyon kontrol hatası ({symbol}): {e}")
    
    @staticmethod
    def get_stats():
        """Portföy istatistikleri"""
        if not PORTFOLIO_HISTORY:
            return None
        
        df = pd.DataFrame(PORTFOLIO_HISTORY)
        
        wins = df[df['pnl_pct'] > 0]
        losses = df[df['pnl_pct'] <= 0]
        
        stats = {
            'total_trades': len(df),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / len(df) * 100 if len(df) > 0 else 0,
            'avg_win': wins['pnl_pct'].mean() if len(wins) > 0 else 0,
            'avg_loss': losses['pnl_pct'].mean() if len(losses) > 0 else 0,
            'total_pnl': df['pnl_pct'].sum(),
            'best_trade': df.loc[df['pnl_pct'].idxmax()] if len(df) > 0 else None,
            'worst_trade': df.loc[df['pnl_pct'].idxmin()] if len(df) > 0 else None,
            'avg_duration': df['duration'].mean()
        }
        
        if len(df) > 1:
            stats['sharpe'] = df['pnl_pct'].mean() / df['pnl_pct'].std() if df['pnl_pct'].std() > 0 else 0
            stats['max_drawdown'] = (df['pnl_pct'].cumsum().cummax() - df['pnl_pct'].cumsum()).max()
        else:
            stats['sharpe'] = 0
            stats['max_drawdown'] = 0
        
        # Risk/Reward ratio
        if len(losses) > 0 and losses['pnl_pct'].mean() != 0:
            stats['risk_reward'] = abs(wins['pnl_pct'].mean() / losses['pnl_pct'].mean()) if len(wins) > 0 else 0
        else:
            stats['risk_reward'] = 0
        
        return stats

# ==========================================
# TECHNICAL INDICATORS
# ==========================================
def calculate_indicators(df):
    """Teknik indikatörleri hesapla"""
    # RSI (Wilder EWM yöntemi — doğru hesaplama)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, min_periods=14).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, min_periods=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    df['ema_12'] = df['close'].ewm(span=12).mean()
    df['ema_26'] = df['close'].ewm(span=26).mean()
    df['macd'] = df['ema_12'] - df['ema_26']
    df['signal'] = df['macd'].ewm(span=9).mean()
    df['macd_hist'] = df['macd'] - df['signal']
    
    # Bollinger Bands
    df['bb_mid'] = df['close'].rolling(window=20).mean()
    bb_std = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['bb_mid'] + (bb_std * 2)
    df['bb_lower'] = df['bb_mid'] - (bb_std * 2)
    
    # BB Width & Squeeze (büyük hareket habercisi)
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']
    df['bb_squeeze'] = df['bb_width'] < df['bb_width'].rolling(120).quantile(0.1)
    
    # EMA — hızlı (9/21) + standart (20/50/200)
    df['ema_9'] = df['close'].ewm(span=9).mean()
    df['ema_21'] = df['close'].ewm(span=21).mean()
    df['ema_20'] = df['close'].ewm(span=20).mean()
    df['ema_50'] = df['close'].ewm(span=50).mean()
    df['ema_200'] = df['close'].ewm(span=200).mean()
    
    # ATR
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['atr'] = true_range.rolling(14).mean()
    
    # Volume indicators
    df['vol_sma'] = df['volume'].rolling(window=20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_sma']

    # Ek İndikatörler (ADX, Stochastic, Ichimoku, VWAP)
    try:
        # ADX (Trend Gücü)
        df['plus_dm'] = df['high'].diff()
        df['minus_dm'] = -df['low'].diff()
        df['plus_dm'] = np.where((df['plus_dm'] > df['minus_dm']) & (df['plus_dm'] > 0), df['plus_dm'], 0)
        df['minus_dm'] = np.where((df['minus_dm'] > df['plus_dm']) & (df['minus_dm'] > 0), df['minus_dm'], 0)
        
        df['plus_di'] = 100 * (df['plus_dm'].rolling(14).mean() / df['atr'])
        df['minus_di'] = 100 * (df['minus_dm'].rolling(14).mean() / df['atr'])
        df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
        df['adx'] = df['dx'].rolling(14).mean()
        
        # Stochastic
        df['lowest_low'] = df['low'].rolling(14).min()
        df['highest_high'] = df['high'].rolling(14).max()
        df['stoch_k'] = 100 * ((df['close'] - df['lowest_low']) / (df['highest_high'] - df['lowest_low']))
        df['stoch_d'] = df['stoch_k'].rolling(3).mean()
        
        # Ichimoku
        df['tenkan'] = (df['high'].rolling(9).max() + df['low'].rolling(9).min()) / 2
        df['kijun'] = (df['high'].rolling(26).max() + df['low'].rolling(26).min()) / 2
        df['senkou_a'] = ((df['tenkan'] + df['kijun']) / 2).shift(26)
        df['senkou_b'] = ((df['high'].rolling(52).max() + df['low'].rolling(52).min()) / 2).shift(26)
        
        # VWAP (günlük reset ile)
        if 'timestamp' in df.columns:
            df['_date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.date
            df['_tp'] = (df['high'] + df['low'] + df['close']) / 3
            df['_cum_vol'] = df.groupby('_date')['volume'].cumsum()
            df['_cum_tp_vol'] = df.groupby('_date').apply(
                lambda x: (x['_tp'] * x['volume']).cumsum()
            ).reset_index(level=0, drop=True)
            df['vwap'] = df['_cum_tp_vol'] / df['_cum_vol']
            df.drop(columns=['_date', '_tp', '_cum_vol', '_cum_tp_vol'], inplace=True, errors='ignore')
        else:
            # Fallback: kümülatif VWAP
            df['vwap'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
    except Exception as e:
        logger.warning(f"Ek indikatör hesaplama uyarısı: {e}")
    
    return df

# ==========================================
# SIGNAL GENERATOR
# ==========================================
@binance_limiter
def multi_timeframe_confirmation(symbol):
    """Çoklu zaman dilimi onayı"""
    try:
        timeframes = {'15m': 0, '1h': 0, '4h': 0}
        
        for tf in timeframes.keys():
            bars = exchange.fetch_ohlcv(symbol, tf, limit=100)
            df = pd.DataFrame(bars, columns=['timestamp','open','high','low','close','volume'])
            df = calculate_indicators(df)
            last = df.iloc[-1]
            
            if (last['close'] > last['ema_20'] and 
                last['ema_20'] > last['ema_50'] and
                last['macd'] > last['signal'] and
                last['adx'] > 25):
                timeframes[tf] = 1  # Bullish
            elif (last['close'] < last['ema_20'] and 
                  last['ema_20'] < last['ema_50'] and
                  last['macd'] < last['signal'] and
                  last['adx'] > 25):
                timeframes[tf] = -1  # Bearish
            
            time.sleep(0.5)
        
        values = list(timeframes.values())
        if all(v == 1 for v in values):
            return 'BULLISH', 3
        elif all(v == -1 for v in values):
            return 'BEARISH', 3
        elif values.count(1) >= 2:
            return 'BULLISH', 2
        elif values.count(-1) >= 2:
            return 'BEARISH', 2
        else:
            return 'NEUTRAL', 0
    except Exception as e:
        logger.warning(f"Multi-TF onay hatası ({symbol}): {e}")
        return 'NEUTRAL', 0

@binance_limiter
def professional_signal_scanner():
    """ULTRA PROFESYONEL SİNYAL - BULL/BEAR AYRIMLI & TEMEL ANALİZ DAHİL"""
    logger.info("🔍 Ultra profesyonel sinyal taraması (Expert Mode)...")
    signals_found = []
    
    # Piyasa rejimi ve sentiment
    regime = MARKET_REGIME.get('current', 'UNKNOWN')
    
    for symbol in SYMBOLS:
        try:
            # 1. Veri Hazırlığı
            bars = exchange.fetch_ohlcv(symbol, '1h', limit=200)
            if len(bars) < 100: continue
            
            df = pd.DataFrame(bars, columns=['timestamp','open','high','low','close','volume'])
            df = calculate_indicators(df)
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            # Puanlama Değişkenleri (Zıt yönler karışmasın diye ayrıldı)
            bull_score = 0
            bear_score = 0
            signals = []
            
            # ==========================================
            # 2. TEKNİK ANALİZ (İNDİKATÖRLER)
            # ==========================================
            
            # RSI (Wilder)
            if last['rsi'] < 30:
                signals.append(f"RSI Oversold ({last['rsi']:.1f})")
                bull_score += 15
            elif last['rsi'] > 70:
                signals.append(f"RSI Overbought ({last['rsi']:.1f})")
                bear_score += 15
                
            # MACD
            if prev['macd'] < prev['signal'] and last['macd'] > last['signal']:
                signals.append("MACD Bullish Cross")
                bull_score += 20
            elif prev['macd'] > prev['signal'] and last['macd'] < last['signal']:
                signals.append("MACD Bearish Cross")
                bear_score += 20
                
            # EMA Cross (Hızlı 9/21 ve Standart 20/50)
            if prev['ema_9'] < prev['ema_21'] and last['ema_9'] > last['ema_21']:
                signals.append("EMA 9/21 Fast Cross")
                bull_score += 15
            elif prev['ema_9'] > prev['ema_21'] and last['ema_9'] < last['ema_21']:
                signals.append("EMA 9/21 Fast Death")
                bear_score += 15
                
            if prev['ema_20'] < prev['ema_50'] and last['ema_20'] > last['ema_50']:
                signals.append("Golden Cross (20/50)")
                bull_score += 25
            elif prev['ema_20'] > prev['ema_50'] and last['ema_20'] < last['ema_50']:
                signals.append("Death Cross (20/50)")
                bear_score += 25
                
            # Bollinger Bands Squeeze
            if last['bb_squeeze']:
                signals.append("BB Squeeze (Patlama Yakın)")
                # Yön tahmini için fiyata bak
                if last['close'] > last['bb_upper']:
                    bull_score += 15
                elif last['close'] < last['bb_lower']:
                    bear_score += 15
            
            # Ichimoku Cloud
            if 'senkou_a' in last:
                # Fiyat bulutun neresinde?
                lead_a = last['senkou_a']
                lead_b = last['senkou_b']
                cloud_top = max(lead_a, lead_b)
                cloud_bottom = min(lead_a, lead_b)
                
                if last['close'] > cloud_top:
                    bull_score += 10
                    if last['tenkan'] > last['kijun']:
                        signals.append("Ichimoku Sinyali (Bulut Üstü + TK Cross)")
                        bull_score += 10
                elif last['close'] < cloud_bottom:
                    bear_score += 10
                    if last['tenkan'] < last['kijun']:
                        signals.append("Ichimoku Satış (Bulut Altı + TK Cross)")
                        bear_score += 10

            # ADX Trend Gücü
            if last['adx'] > 25:
                if last['plus_di'] > last['minus_di']:
                    bull_score += 10  # Güçlü trend desteği
                else:
                    bear_score += 10

            # ==========================================
            # 3. TEMEL & PİYASA ANALİZİ
            # ==========================================
            
            # Volume Confirmation
            if last['vol_ratio'] > 2.0:
                signals.append(f"High Volume ({last['vol_ratio']:.1f}x)")
                # Volume, baskın olan yönü güçlendirir
                if bull_score > bear_score: bull_score += 15
                elif bear_score > bull_score: bear_score += 15
            elif last['vol_ratio'] < 0.8:
                # Hacimsiz yükseliş/düşüş güvenilmezdir
                bull_score *= 0.9
                bear_score *= 0.9
                
            # Multi-Timeframe (Cache'li)
            # Her seferinde API çağrısı yapmamak için basit cache mantığı eklenebilir
            # Şimdilik doğrudan çağırıyoruz ama time.sleep ile
            mtf_trend, mtf_strength = multi_timeframe_confirmation(symbol)
            if mtf_trend == 'BULLISH':
                signals.append(f"MTF Bullish (Güç: {mtf_strength})")
                bull_score += (mtf_strength * 10)
            elif mtf_trend == 'BEARISH':
                signals.append(f"MTF Bearish (Güç: {mtf_strength})")
                bear_score += (mtf_strength * 10)
                
            # Order Book Analizi
            ob_analysis = OrderBookAnalyzer.analyze_order_book(symbol)
            if ob_analysis:
                if ob_analysis['sentiment'] == 'BULLISH':
                    bull_score += 10
                elif ob_analysis['sentiment'] == 'BEARISH':
                    bear_score += 10
            
            # Haber Sentiment iptal edildi, sadece temel ve teknik göstergeler puanı etkiler.

            # ==========================================
            # 4. KARAR MEKANİZMASI
            # ==========================================
            
            # Market Regime Filtresi
            # Range piyasasında trend sinyallerinin güvenini düşür
            threshold = 85  # Sniper Mode: 85 (Eski: 75)
            
            if regime == 'RANGING':
                threshold = 90  # Range'de daha seçici ol (Eski: 85)
                # RSI 30/70 sinyalleri range'de daha değerlidir
                if any('RSI' in s for s in signals):
                    if bull_score > bear_score: bull_score += 10
                    else: bear_score += 10
            elif regime == 'TRENDING':
                threshold = 80  # Trend varsa puana daha az ihtiyaç var (Eski: 70)
            
            # CONFLUENCE CHECK (ZORUNLU ONAY)
            # Sinyal sadece Hacim veya Güçlü Trend varsa geçerlidir
            has_volume = last['vol_ratio'] > 2.0
            has_trend = (last['adx'] > 30) if 'adx' in last else False
            
            if not (has_volume or has_trend):
                # Zayıf sinyal - Reddet
                bull_score = 0
                bear_score = 0
            
            final_signal = None
            final_score = 0
            
            if bull_score > threshold and bull_score > (bear_score * 1.5):
                final_signal = 'BUY'
                final_score = bull_score
            elif bear_score > threshold and bear_score > (bull_score * 1.5):
                final_signal = 'SELL'
                final_score = bear_score
            
            if final_signal:
                signals_found.append({
                    'symbol': symbol,
                    'type': final_signal,
                    'price': last['close'],
                    'confidence': min(int(final_score), 100),
                    'signals': signals,
                    'timestamp': str(datetime.now()),
                    'reason': ', '.join(signals[:5])
                })
                
                # Signal History & DB Update
                SIGNAL_HISTORY.append(signals_found[-1])
                Database.save_signal(signals_found[-1])
                logger.info(f"� UZMAN SİNYAL: {symbol} {final_signal} | Skor: {final_score}")
                
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Sinyal hatası ({symbol}): {e}")
            continue
    
    # Telegram'a gönder
    if signals_found:
        top = sorted(signals_found, key=lambda x: x['confidence'], reverse=True)[:3]
        
        msg = "🎯 **YÜKSEK KALİTE SİNYALLER!**\n*(Çok sıkı filtrelerden geçti)*\n\n"
        
        for sig in top:
            emoji = '🟢' if sig['type'] == 'BUY' else '🔴'
            msg += f"{emoji} **{sig['symbol']}** - {sig['type']}\n"
            msg += f"💰 ${sig['price']:.2f}\n"
            msg += f"⭐ Güven: **{sig['confidence']}/100**\n"
            msg += f"🔍 Sinyaller:\n"
            for s in sig['signals'][:4]:
                msg += f"  • {s}\n"
            msg += "\n"
            
            # Yönetici Bot (Kaan Kimliği)
            if sig['confidence'] >= 85:
                pred_mock = {
                    'confidence': sig['confidence'],
                    'direction': 'YUKARI' if sig['type'] == 'BUY' else 'AŞAĞI',
                    'reasons': sig['signals'][:3]
                }
                AutoTrader.execute_trade(sig['symbol'], sig['price'], pred_mock, is_margin=False)
        
        safe_send_message(TELEGRAM_CHAT_ID, msg)
    
    logger.info(f"✅ {len(signals_found)} YÜKSEK KALİTE sinyal")

# ============================= ORIJINAL KODUN DEVAMI =============================
# (Backtester, MLPredictor, OrderBookAnalyzer, vb. tüm sınıflar aynen korundu)
# ==================================================================================

class Backtester:
    """Strateji backtesting"""
    
    @staticmethod
    def run_backtest(symbol, months=6):
        """Backtest çalıştır"""
        try:
            logger.info(f"🔄 Backtest başlatılıyor: {symbol} ({months} ay)")
            
            since = int((datetime.now() - timedelta(days=months*30)).timestamp() * 1000)
            
            all_bars = []
            while True:
                bars = exchange.fetch_ohlcv(symbol, '1h', since=since, limit=1000)
                if not bars:
                    break
                all_bars.extend(bars)
                if len(bars) < 1000:
                    break
                since = bars[-1][0] + 1
                time.sleep(1)
            
            if len(all_bars) < 100:
                return None
            
            df = pd.DataFrame(all_bars, columns=['timestamp','open','high','low','close','volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = calculate_indicators(df)
            
            # Backtest logic
            capital = 1000
            position = None
            trades = []
            
            FEE = 0.001       # %0.1 Komisyon
            SLIPPAGE = 0.001  # %0.1 Kayma
            
            for i in range(50, len(df)):
                current = df.iloc[i]
                prev = df.iloc[i-1]
                
                # Entry signals
                if position is None:
                    # LONG Sinyali
                    if (current['rsi'] < 30 and 
                        current['macd'] > current['signal'] and
                        current['close'] > current['ema_20']):
                        
                        position = {
                            'entry_price': current['close'] * (1 + SLIPPAGE), # Kayma ile giriş
                            'entry_time': current['timestamp'],
                            'type': 'LONG',
                            'amount': capital / (current['close'] * (1 + SLIPPAGE))
                        }
                        capital -= (capital * FEE) # Komisyon düş
                        
                    # SHORT Sinyali
                    elif (current['rsi'] > 70 and
                          current['macd'] < current['signal'] and
                          current['close'] < current['ema_20']):
                        
                         position = {
                            'entry_price': current['close'] * (1 - SLIPPAGE), # Kayma ile giriş
                            'entry_time': current['timestamp'],
                            'type': 'SHORT',
                            'amount': capital / (current['close'] * (1 - SLIPPAGE))
                        }
                         capital -= (capital * FEE) # Komisyon düş
                
                # Exit signals
                elif position is not None:
                    # Mevcut PnL
                    if position['type'] == 'LONG':
                        exit_price = current['close'] * (1 - SLIPPAGE)
                        pnl_pct = ((exit_price - position['entry_price']) / position['entry_price']) * 100
                    else: # SHORT
                        exit_price = current['close'] * (1 + SLIPPAGE)
                        pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price']) * 100
                    
                    # Take profit or stop loss
                    # TP: %5, SL: %3 veya RSI Ters Sinyal
                    is_exit = False
                    reason = ''
                    
                    if pnl_pct >= 5:
                        is_exit = True; reason = 'TP'
                    elif pnl_pct <= -3:
                        is_exit = True; reason = 'SL'
                    elif position['type'] == 'LONG' and current['rsi'] > 75:
                        is_exit = True; reason = 'RSI Overbought'
                    elif position['type'] == 'SHORT' and current['rsi'] < 25:
                        is_exit = True; reason = 'RSI Oversold'
                        
                    if is_exit:
                        # Bakiyeyi güncelle
                        if position['type'] == 'LONG':
                            capital = position['amount'] * exit_price
                        else:
                            # Short: Başlangıç teminatı + Kâr/Zarar
                            initial_value = position['amount'] * position['entry_price']
                            profit = initial_value * (pnl_pct / 100)
                            capital = initial_value + profit
                            
                        capital -= (capital * FEE) # Çıkış komisyonu
                        
                        trade = {
                            'entry': position['entry_price'],
                            'exit': exit_price,
                            'pnl_pct': pnl_pct,
                            'type': position['type'],
                            'reason': reason,
                            'duration': (current['timestamp'] - position['entry_time']).total_seconds() / 3600
                        }
                        trades.append(trade)
                        position = None
            
            if len(trades) == 0:
                logger.info(f"⚠️ Backtest: {symbol} için hiç trade yapılmadı.")
                return None
            
            trades_df = pd.DataFrame(trades)
            wins = trades_df[trades_df['pnl_pct'] > 0]
            losses = trades_df[trades_df['pnl_pct'] <= 0]
            
            # Sharpe Ratio (Yıllıklandırılmış ve Risk-free rate dahil)
            # Risk-free rate varsayımı: %5 yıllık -> günlük %0.0137 -> trade başına yaklaşık (ortalama süreye göre değişir ama basitleştiriyoruz)
            # Daha doğru: (Mean Returns - RiskFree) / StdDev
            risk_free_rate = 0.0
            avg_return = trades_df['pnl_pct'].mean()
            std_dev = trades_df['pnl_pct'].std()
            
            if std_dev > 0:
                sharpe = (avg_return - risk_free_rate) / std_dev * np.sqrt(len(trades_df)) # Yaklaşık yıllıklandırma
            else:
                sharpe = 0
            
            result = {
                'symbol': symbol,
                'total_trades': len(trades_df),
                'wins': len(wins),
                'losses': len(losses),
                'win_rate': len(wins) / len(trades_df) * 100,
                'avg_win': wins['pnl_pct'].mean() if len(wins) > 0 else 0,
                'avg_loss': losses['pnl_pct'].mean() if len(losses) > 0 else 0,
                'total_pnl': ((capital - 1000) / 1000) * 100, # Başlangıç 1000 varsayımıyla % değişim
                'final_capital': capital,
                'sharpe': sharpe
            }
            
            BACKTEST_RESULTS[symbol] = result
            logger.info(f"✅ Backtest tamamlandı: {symbol} | Win Rate: {result['win_rate']:.1f}% | Net PnL: {result['total_pnl']:.2f}%")
            
            return result
            
        except Exception as e:
            logger.error(f"Backtest hatası ({symbol}): {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

class CorrelationAnalyzer:
    """Coin korelasyon analizi"""
    
    @staticmethod
    def calculate_correlations(days=30):
        """Korelasyon matrisini hesapla"""
        try:
            logger.info("📊 Korelasyon hesaplanıyor...")
            
            price_data = {}
            
            for symbol in SYMBOLS[:8]:  # İlk 8 coin
                try:
                    bars = exchange.fetch_ohlcv(symbol, '1d', limit=days)
                    closes = [b[4] for b in bars]
                    price_data[symbol] = closes
                    time.sleep(0.5)
                except:
                    continue
            
            if len(price_data) < 2:
                return None
            
            df = pd.DataFrame(price_data)
            corr_matrix = df.corr()
            
            CORRELATION_DATA['matrix'] = corr_matrix
            CORRELATION_DATA['timestamp'] = datetime.now()
            
            # En yüksek korelasyonlar
            high_corr = []
            for i in range(len(corr_matrix)):
                for j in range(i+1, len(corr_matrix)):
                    corr_val = corr_matrix.iloc[i, j]
                    if abs(corr_val) > 0.7:
                        high_corr.append({
                            'pair': f"{corr_matrix.index[i]} - {corr_matrix.columns[j]}",
                            'correlation': corr_val
                        })
            
            CORRELATION_DATA['high_correlations'] = sorted(high_corr, key=lambda x: abs(x['correlation']), reverse=True)
            
            logger.info(f"✅ Korelasyon hesaplandı. {len(high_corr)} yüksek korelasyon bulundu.")
            return corr_matrix
            
        except Exception as e:
            logger.error(f"Korelasyon hatası: {e}")
            return None

class MLPredictor:
    """Makine Öğrenmesi ile Fiyat Tahmini"""
    
    @staticmethod
    def prepare_features(df):
        """ML özellikleri hazırla (Genişletilmiş)"""
        features = pd.DataFrame()
        
        # Trend
        features['rsi'] = df['rsi']
        features['macd'] = df['macd']
        features['macd_hist'] = df['macd_hist']
        features['macd_signal'] = df['signal']
        features['adx'] = df['adx'] if 'adx' in df else 50
        
        # Volatilite & Momentum
        features['bb_width'] = df['bb_width'] if 'bb_width' in df else 0
        features['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        features['stoch_k'] = df['stoch_k'] if 'stoch_k' in df else 50
        
        # Moving Averages
        features['ema_20_50'] = df['ema_20'] / df['ema_50']
        features['close_sma_ratio'] = df['close'] / df['ema_20']
        
        # Volume & Price Action
        features['vol_ratio'] = df['vol_ratio']
        features['atr'] = df['atr']
        features['returns_1'] = df['close'].pct_change(1)
        features['returns_5'] = df['close'].pct_change(5)
        
        # VWAP & Time
        if 'vwap' in df:
            features['close_vwap'] = df['close'] / df['vwap']
            
        if 'timestamp' in df:
            dt = pd.to_datetime(df['timestamp'], unit='ms')
            features['hour'] = dt.dt.hour
            features['dayofweek'] = dt.dt.dayofweek
        
        return features.replace([np.inf, -np.inf], np.nan).dropna()
    
    @staticmethod
    def train_model(symbol):
        """Model eğit (TimeSeriesSplit ile)"""
        try:
            logger.info(f"🧠 ML model eğitiliyor: {symbol}")
            
            # Daha fazla veri çek (Binance limitine uygun)
            bars = exchange.fetch_ohlcv(symbol, '1h', limit=1000)
            
            if len(bars) < 500:
                return None
            
            df = pd.DataFrame(bars, columns=['timestamp','open','high','low','close','volume'])
            df = calculate_indicators(df)
            
            features = MLPredictor.prepare_features(df)
            
            # Target: Next hour price direction
            df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
            
            # Feature ve Target eşlemesi
            common_index = features.index.intersection(df.index[:-1])
            X = features.loc[common_index]
            y = df['target'].loc[common_index]
            
            # TimeSeriesSplit Validation
            tscv = TimeSeriesSplit(n_splits=5)
            scores = []
            
            # Scale features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            model = RandomForestClassifier(n_estimators=200, max_depth=15, min_samples_split=5, random_state=42)
            
            for train_index, test_index in tscv.split(X_scaled):
                X_train, X_test = X_scaled[train_index], X_scaled[test_index]
                y_train, y_test = y.iloc[train_index], y.iloc[test_index]
                
                model.fit(X_train, y_train)
                scores.append(model.score(X_test, y_test))
            
            avg_accuracy = np.mean(scores)
            
            # Final training on all data
            model.fit(X_scaled, y)
            
            ML_MODELS[symbol] = {
                'model': model,
                'scaler': scaler,
                'accuracy': avg_accuracy,
                'trained_at': datetime.now()
            }
            
            logger.info(f"✅ Model eğitildi: {symbol} | Accuracy: {avg_accuracy*100:.1f}% (CV)")
            return model
            
        except Exception as e:
            logger.error(f"ML eğitim hatası ({symbol}): {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    @staticmethod
    def predict(symbol):
        """Tahmin yap ve nedenlerini açıkla"""
        try:
            if symbol not in ML_MODELS:
                MLPredictor.train_model(symbol)
            
            if symbol not in ML_MODELS:
                return None
            
            model_data = ML_MODELS[symbol]
            model = model_data['model']
            scaler = model_data['scaler']
            
            # Veri çek
            bars = exchange.fetch_ohlcv(symbol, '1h', limit=100)
            df = pd.DataFrame(bars, columns=['timestamp','open','high','low','close','volume'])
            df = calculate_indicators(df)
            
            # Feature hazırlığı
            features = MLPredictor.prepare_features(df)
            if features.empty: return None
            
            last_features = features.iloc[[-1]]
            last_scaled = scaler.transform(last_features)
            
            # Tahmin
            prediction = model.predict(last_scaled)[0]
            proba = model.predict_proba(last_scaled)[0]
            confidence = max(proba) * 100
            
            # Order Book Analizi (Extra Teyit)
            ob_analysis = OrderBookAnalyzer.analyze_order_book(symbol)
            ob_imbalance = ob_analysis.get('imbalance_pct', 0) if ob_analysis else 0
            
            # "Neden?" Analizi (Explainability)
            reasons = []
            row = df.iloc[-1]
            
            # RSI Durumu
            if row['rsi'] < 30: reasons.append(f"RSI Dipte ({row['rsi']:.1f})")
            elif row['rsi'] > 70: reasons.append(f"RSI Zirvede ({row['rsi']:.1f})")
            
            # Trend Durumu
            if row['adx'] > 25: reasons.append(f"Güçlü Trend (ADX {row['adx']:.1f})")
            
            # Hacim Durumu
            if row['vol_ratio'] > 1.5: reasons.append(f"Hacim Artışı ({row['vol_ratio']:.1f}x)")
            
            # Order Book Durumu
            if ob_imbalance > 10: reasons.append("Order Book: ALICILAR Baskın")
            elif ob_imbalance < -10: reasons.append("Order Book: SATICILAR Baskın")
            
            # Hareketli Ortalamalar
            if row['close'] > row['ema_20']: reasons.append("Fiyat > EMA20 (Pozitif)")
            else: reasons.append("Fiyat < EMA20 (Negatif)")
            
            # Risk Analizi
            risks = []
            if row['rsi'] > 75: risks.append("⚠️ Aşırı Alım Riski (RSI > 75)")
            elif row['rsi'] < 25: risks.append("⚠️ Aşırı Satım Riski (RSI < 25)")
            if row.get('adx', 0) < 20: risks.append("⚠️ Zayıf Trend (ADX < 20)")
            if row.get('vol_ratio', 1.0) < 0.8: risks.append("⚠️ Düşük Hacim")
            
            # Teknik Özet
            tech_summary = {
                'rsi': row['rsi'],
                'adx': row.get('adx', 0),
                'ema_diff': (row['close'] - row['ema_20']) / row['ema_20'] * 100,
                'vol_ratio': row.get('vol_ratio', 1.0)
            }
            
            direction = 'YUKARI' if prediction == 1 else 'AŞAĞI'
            
            return {
                'symbol': symbol,
                'direction': direction,
                'confidence': confidence,
                'accuracy': model_data['accuracy'],
                'reasons': reasons,
                'risks': risks,
                'technical': tech_summary,
                'ob_imbalance': ob_imbalance,
                'price': float(row['close'])
            }
            
        except Exception as e:
            logger.error(f"ML tahmin hatası ({symbol}): {e}")
            return None

class OrderBookAnalyzer:
    """Order book derinlik analizi"""
    
    @staticmethod
    def analyze_order_book(symbol, depth=20):
        """Order book analiz et"""
        try:
            orderbook = exchange.fetch_order_book(symbol, limit=depth)
            
            bids = orderbook['bids'][:depth]
            asks = orderbook['asks'][:depth]
            
            total_bid_volume = sum([b[1] for b in bids])
            total_ask_volume = sum([a[1] for a in asks])
            
            imbalance = total_bid_volume / total_ask_volume if total_ask_volume > 0 else 0
            
            # Big walls
            bid_threshold = total_bid_volume / depth * 3
            ask_threshold = total_ask_volume / depth * 3
            
            big_bids = [{'price': b[0], 'amount': b[1]} for b in bids if b[1] > bid_threshold]
            big_asks = [{'price': a[0], 'amount': a[1]} for a in asks if a[1] > ask_threshold]
            
            sentiment = 'BULLISH' if imbalance > 1.5 else 'BEARISH' if imbalance < 0.7 else 'NEUTRAL'
            
            return {
                'symbol': symbol,
                'imbalance': imbalance,
                'sentiment': sentiment,
                'big_bids': big_bids[:5],
                'big_asks': big_asks[:5],
                'total_bid_vol': total_bid_volume,
                'total_ask_vol': total_ask_volume
            }
            
        except Exception as e:
            logger.error(f"Order book hatası ({symbol}): {e}")
            return None

class PositionSizer:
    """Kelly Criterion position sizing"""
    
    @staticmethod
    def calculate_kelly(symbol):
        """Kelly criterion hesapla"""
        try:
            # Geçmiş trade'leri filtrele
            symbol_trades = [t for t in PORTFOLIO_HISTORY if t['symbol'] == symbol]
            
            if len(symbol_trades) < 10:
                return {'note': 'Yetersiz veri (min 10 trade gerekli)'}
            
            df = pd.DataFrame(symbol_trades)
            
            wins = df[df['pnl_pct'] > 0]
            losses = df[df['pnl_pct'] <= 0]
            
            win_rate = len(wins) / len(df)
            avg_win = wins['pnl_pct'].mean() / 100 if len(wins) > 0 else 0
            avg_loss = abs(losses['pnl_pct'].mean()) / 100 if len(losses) > 0 else 0
            
            if avg_loss == 0:
                return {'note': 'Hesaplanamadı (ortalama kayıp = 0)'}
            
            # Kelly Formula: W - (1-W)/R
            win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
            kelly_pct = (win_rate - (1 - win_rate) / win_loss_ratio) * 100
            
            # Limit to reasonable range
            kelly_pct = max(0, min(kelly_pct, 25))
            
            return {
                'symbol': symbol,
                'kelly': kelly_pct,
                'recommended': kelly_pct * 0.5,  # Half Kelly for safety
                'win_rate': win_rate * 100,
                'avg_win': avg_win * 100,
                'avg_loss': avg_loss * 100,
                'trades': len(df)
            }
            
        except Exception as e:
            logger.error(f"Kelly hesaplama hatası ({symbol}): {e}")
            return {'note': 'Hesaplama hatası'}

class TweetGenerator:
    """Yapay Zeka Destekli Tweet Analiz Üretici"""
    
    @staticmethod
    def generate_tweet(symbol, df, signals=None):
        """Grafik verilerinden profesyonel tweet oluştur"""
        try:
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            # 1. Fiyat Hareketi
            price = last['close']
            change_24h = ((last['close'] - df.iloc[-24]['close']) / df.iloc[-24]['close']) * 100 if len(df) > 24 else 0
            trend_emoji = "🚀" if change_24h > 0 else "🩸"
            
            # 2. Teknik Durum
            rsi = last['rsi']
            adx = last.get('adx', 0)
            ema_20 = last['ema_20']
            
            technical_sentiment = "Nötr"
            if rsi > 70: technical_sentiment = "Aşırı Alım (Düzeltme Riski)"
            elif rsi < 30: technical_sentiment = "Aşırı Satım (Tepki Beklentisi)"
            elif price > ema_20: technical_sentiment = "Yükseliş Trendi Korunuyor"
            else: technical_sentiment = "Düşüş Baskısı Hakim"
            
            # 3. Hacim Analizi
            vol_ratio = last.get('vol_ratio', 1.0)
            vol_comment = "Hacim zayıf"
            if vol_ratio > 2.0: vol_comment = "🔥 Hacim PATLAMASI var!"
            elif vol_ratio > 1.2: vol_comment = "Hacim ortalama üzeri."
            
            # 4. Hedefler (Basit Pivot/Destek-Direnç)
            # 20 mumluk en yüksek/en düşük
            recent_high = df['high'].rolling(20).max().iloc[-1]
            recent_low = df['low'].rolling(20).min().iloc[-1]
            
            support = recent_low
            resistance = recent_high
            
            # Tweet Taslağı
            tweet = f"📢 #{symbol.split('/')[0]} GÜNCEL ANALİZ {trend_emoji}\n\n"
            tweet += f"💰 Fiyat: ${price:.2f} ({change_24h:+.2f}%)\n"
            tweet += f"📊 Trend: {technical_sentiment}\n\n"
            
            tweet += "🔍 **Teknik Görünüm:**\n"
            tweet += f"• RSI: {rsi:.1f} ({'Sıcak' if rsi>60 else 'Soğuk' if rsi<40 else 'Nötr'})\n"
            tweet += f"• ADX: {adx:.1f} ({'Güçlü Trend' if adx>25 else 'Zayıf/Yatay'})\n"
            tweet += f"• {vol_comment}\n\n"
            
            tweet += "🎯 **Seviyeler:**\n"
            tweet += f"🛡️ Destek: ${support:.2f}\n"
            tweet += f"⚔️ Direnç: ${resistance:.2f}\n\n"
            
            tweet += "💡 **Yorumum:**\n"
            fallback_text = ""
            if price > ema_20 and rsi < 70:
                fallback_text = f"{symbol.split('/')[0]} trendi pozitif, ${support:.4f} desteği üzerinde kalıcılık önemli. Geri çekilmeler alım fırsatı sunabilir. 🐂"
            elif price < ema_20 and rsi > 30:
                fallback_text = f"{symbol.split('/')[0]}'da satış baskısı sürüyor. ${support:.4f} desteğinde tutunamazsa düşüş derinleşebilir. 🐻"
            else:
                fallback_text = f"Piyasa kararsız (Ranging). Kırılım yönüne göre işlem alınmalı. Kritik direnç: ${resistance:.4f} 👀"

            if GEMINI_API_KEY:
                try:
                    summary_prompt = f"""
                    Sen anonim uzman bir kripto trader'sın. {symbol} için şu verileri kullanarak kısa, profesyonel ve etkileyici bir VIP analiz yorumu yaz (tweet formatında).
                    Fiyat: ${price:.4f}, Destek: ${support:.4f}, Direnç: ${resistance:.4f}, RSI: {rsi:.1f}, Trend: {technical_sentiment}.
                    Genel geçer ("45k üzeri kalıcılık vb.") ifadeler asla kullanma, sadece bu coine özel yorum yap. İnsan gibi samimi ama anonim bir üslupla 2 cümleyi aşmayacak kalitede yaz. Asla isim kullanma.
                    """
                    response = client.models.generate_content(
                        model=GEN_MODEL,
                        contents=summary_prompt
                    )
                    tweet += response.text.strip()
                except Exception as e:
                    logger.error(f"Gemini tweet yorum hatası: {e}")
                    tweet += fallback_text
            else:
                tweet += fallback_text
                
            tweet += "\n\n#Bitcoin #Crypto #Trading #Analysis"
            tweet += f"\n\n👉 Telegram: {TELEGRAM_CHANNEL_LINK}"
            tweet += f"\n🔗 Linktree: {LINKTREE_LINK}"
            
            return tweet
            
        except Exception as e:
            logger.error(f"Tweet üretim hatası: {e}")
            return f"❌ Analiz oluşturulamadı: {symbol}"



class AutoTrader:
    """İnsan Gibi İşlem Yapan Yönetici Bot (100K Bakiye)"""
    capital = 100000.0  # Toplam Kasa (Sanal)
    active_trades = {}  # {symbol: {'entry_price': ..., 'size': ..., 'leverage': ..., 'direction': ..., 'capital_used': ...}}
    
    @staticmethod
    def execute_trade(symbol, current_price, pred, is_margin=False):
        """100K kasadan belirli risk (örn. %5) ayırarak işlemi açar."""
        if symbol in AutoTrader.active_trades:
            return  # Zaten açık pozisyon var
            
        try:
            # İşlem Başına Risk (%5)
            risk_pct = 0.05
            capital_used = AutoTrader.capital * risk_pct
            
            # Kaldıraç Belirleme (Sinyal Güvenine göre)
            leverage = 1
            if is_margin and pred['confidence'] > 85:
                # 80 üstü güven 2x-10x arası
                leverage = int(np.clip((pred['confidence'] - 80) / 2, 2, 10))
            elif is_margin:
                leverage = 3
                
            direction = pred.get('direction', 'YUKARI')
            reasons = ", ".join(pred.get('reasons', ['Dinamik işlem stratejisi'])[:2])
            
            AutoTrader.active_trades[symbol] = {
                'entry_price': current_price,
                'entry_time': datetime.now(),
                'direction': direction,
                'capital_used': capital_used,
                'leverage': leverage,
                'reason': reasons,
                'confidence': pred.get('confidence', 80)
            }
            
            logger.info(f"👨‍💼 YÖNETİCİ İŞLEME GİRDİ: {symbol} | Yön: {direction} | Büyüklük: ${capital_used:.0f}x{leverage}")
            
            # Telegram'a Kaan Ağzıyla Mesaj
            AutoTrader.send_human_entry_message(symbol, direction, current_price, capital_used, leverage, reasons, pred)
            
        except Exception as e:
            logger.error(f"AutoTrader giriş hatası ({symbol}): {e}")

    @staticmethod
    def send_human_entry_message(symbol, direction, price, capital_used, leverage, reasons, pred):
        try:
            prompt = f'''
            Sen anonim profesyonel bir kripto traderısın. Telegram kanalında takipçilerine kendi girdiğin bir işlemi duyuruyorsun. Hiçbir isim kullanma.
            İşlem verileri:
            - Coin: {symbol}
            - Yön: {'Long (Yükseliş)' if direction == 'YUKARI' else 'Short (Düşüş)' if direction == 'AŞAĞI' else 'Spot Alım'}
            - Giriş Fiyatı: ${price:.4f}
            - Kasa Kullanımı: $100.000'lık kasanın ${capital_used:.0f} kadarı ile
            - Kaldıraç: {leverage}x
            - Teknik Nedenler: {reasons}
            
            Samimi, doğal bir insan ağzıyla, emojiler kullanarak 2-3 cümlelik bir mesaj yaz. Bot gibi konuşma. Telegram kanalına yazıyormuş gibi hissettir. "Herkese selamlar, ben şuradan giriyorum" de fakat Kaan veya başka bir isim kesinlikle kullanma.
            '''
            
            msg = None
            if GEMINI_API_KEY:
                try:
                    response = client.models.generate_content(model=GEN_MODEL, contents=prompt)
                    msg = response.text.strip()
                except Exception as e:
                    logger.warning(f"Gemini API hatası (Yedek mesaja geçiliyor): {str(e)[:100]}")
            
            if not msg:
                msg = f"Dostlar selam, {symbol}'de güzel bir fırsat yakaladım. Nedenler: {reasons}. Bu yüzden ${price:.4f} seviyesinden {leverage}x {'Long' if direction=='YUKARI' else 'Short'} giriyorum. Kasamın ufak bir kısmıyla (${capital_used:.0f}) deniyorum, herkese bol kazançlar. 🚀"
            
            # Hashtagler ve linkler
            coin_tag = symbol.split('/')[0]
            hashtags = f"\n\n#{coin_tag} #Kripto #Sinyal #Trading #Bitcoin #Altcoin"
            
            full_msg = f"👨‍💼 **YENİ İŞLEM**\n\n{msg}{hashtags}\n\n👉 {TELEGRAM_CHANNEL_LINK}\n🔗 {LINKTREE_LINK}"
            
            safe_send_message(TELEGRAM_CHAT_ID, full_msg)
            
            # Özel mesaj (Tweet atmak için kopyala-yapıştır dostu)
            if VIP_USER_ID:
                tweet_reminder = "💡 **TWEET ATMAK İÇİN KOPYALA:**\n\n"
                safe_send_message(VIP_USER_ID, tweet_reminder + full_msg)
        except Exception as e:
            logger.error(f"Yönetici mesaj hatası: {e}")

    @staticmethod
    def check_active_trades():
        """Açık işlemleri kontrol et (Stop/TP)"""
        try:
            symbols_to_close = []
            for symbol, pos in list(AutoTrader.active_trades.items()):
                try:
                    ticker = exchange.fetch_ticker(symbol)
                except:
                    continue
                current_price = ticker['last']
                
                entry = pos['entry_price']
                leverage = pos['leverage']
                
                # Kar/Zarar Yüzdesi (Kaldıraçlı)
                if pos['direction'] == 'YUKARI':
                    raw_change = (current_price - entry) / entry
                else:  # AŞAĞI (Short)
                    raw_change = (entry - current_price) / entry
                    
                pnl_pct = raw_change * 100 * leverage
                
                # Çıkış şartları (Geliştirilmiş ve Gerçekçi)
                if pnl_pct >= 5.0:  # %5 Kar AL
                    reason = "Take Profit (%5)"
                    symbols_to_close.append((symbol, pnl_pct, reason))
                elif pnl_pct <= -3.0:  # %3 Stop Loss
                    reason = "Stop Loss (%3)"
                    symbols_to_close.append((symbol, pnl_pct, reason))
                
                # Basit Takipçi Stop (Kâr %5'i geçtiyse ve %2 geri çekilirse kapat)
                if 'max_pnl' not in pos: pos['max_pnl'] = pnl_pct
                if pnl_pct > pos['max_pnl']: pos['max_pnl'] = pnl_pct
                
                if pos['max_pnl'] >= 4.0 and (pos['max_pnl'] - pnl_pct) >= 2.0:
                    reason = f"Trailing Exit (Zirveden %2 düşüş, Max: %{pos['max_pnl']:.1f})"
                    symbols_to_close.append((symbol, pnl_pct, reason))
                    
            for symbol, pnl_pct, reason in symbols_to_close:
                pos = AutoTrader.active_trades.pop(symbol)
                # Kasayı güncelle
                pnl_amount = pos['capital_used'] * (pnl_pct / 100)
                AutoTrader.capital += pnl_amount
                
                AutoTrader.send_human_exit_message(symbol, pnl_pct, pnl_amount, reason)
                
        except Exception as e:
            logger.error(f"Yönetici işlem kontrol hatası: {e}")

    @staticmethod
    def send_human_exit_message(symbol, pnl_pct, pnl_amount, reason):
        try:
            prompt = f'''
            Sen anonim bir kripto traderısın. Telegram'da takipçilerine demin açtığın {symbol} işleminin kapandığını duyuruyorsun. İsim veya "Kaan" kelimesi KESİNLİKLE kullanma.
            Sonuç: %{pnl_pct:.2f} {'Kâr' if pnl_pct > 0 else 'Zarar'}
            Net Para: ${abs(pnl_amount):.2f} {'Kazanıldı' if pnl_amount > 0 else 'Kaybedildi'}
            Kapanma Nedeni: {reason}
            Güncel Kasa: ${AutoTrader.capital:.2f}
            
            {'Harika kâr aldık, bereket versin.' if pnl_pct > 0 else 'Sağlık olsun, piyasa terste bıraktı, stop olduk.'} minvalinde 2 cümlelik samimi bir insan mesajı yaz.
            '''
            msg = None
            if GEMINI_API_KEY:
                try:
                    response = client.models.generate_content(model=GEN_MODEL, contents=prompt)
                    msg = response.text.strip()
                except Exception as e:
                    logger.warning(f"Gemini API hatası (Yedek mesaja geçiliyor): {str(e)[:100]}")
            
            if not msg:
                if pnl_pct > 0:
                    msg = f"Güzel işlem oldu dostlar, {symbol}'den %{pnl_pct:.2f} kârla ayrılıyorum (+${pnl_amount:.2f}). Bereket versin! 💰 Güncel kasa: ${AutoTrader.capital:.2f}"
                else:
                    msg = f"Can sıkıcı ama {symbol}'de stop olduk arkadaşlar. %{abs(pnl_pct):.2f} zarar (-${abs(pnl_amount):.2f}) yazdık, sağlık olsun fırsat bitmez. 🛡️ Güncel kasa: ${AutoTrader.capital:.2f}"
            
            safe_send_message(TELEGRAM_CHAT_ID, f"👨‍💼 **İŞLEM SONUCU**\n\n{msg}\n\n👉 {TELEGRAM_CHANNEL_LINK}")
        except Exception as e:
            logger.error(f"Yönetici çıkış mesaj hatası: {e}")

class MarketRegimeDetector:
    """Piyasa rejimi tespiti (Trend/Range/Volatile)"""
    
    @staticmethod
    def detect_regime(symbol='BTC/USDT'):
        """Piyasa rejimini tespit et"""
        try:
            bars = exchange.fetch_ohlcv(symbol, '4h', limit=100)
            df = pd.DataFrame(bars, columns=['timestamp','open','high','low','close','volume'])
            
            # Volatilite
            returns = df['close'].pct_change()
            volatility = returns.std() * np.sqrt(24)  # Annualized
            
            # Trend strength (ADX benzeri)
            df['high_low'] = df['high'] - df['low']
            df['high_close'] = abs(df['high'] - df['close'].shift())
            df['low_close'] = abs(df['low'] - df['close'].shift())
            df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
            df['atr'] = df['tr'].rolling(14).mean()
            
            # Directional movement
            df['up_move'] = df['high'] - df['high'].shift()
            df['down_move'] = df['low'].shift() - df['low']
            
            df['dm_plus'] = np.where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), df['up_move'], 0)
            df['dm_minus'] = np.where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), df['down_move'], 0)
            
            df['di_plus'] = 100 * (df['dm_plus'].rolling(14).mean() / df['atr'])
            df['di_minus'] = 100 * (df['dm_minus'].rolling(14).mean() / df['atr'])
            
            df['dx'] = 100 * abs(df['di_plus'] - df['di_minus']) / (df['di_plus'] + df['di_minus'])
            df['adx'] = df['dx'].rolling(14).mean()
            
            last_adx = df['adx'].iloc[-1]
            
            # Regime classification
            if volatility > 0.6:
                regime = 'VOLATILE'
                confidence = min(volatility / 0.6, 1.0)
            elif last_adx > 25:
                regime = 'TRENDING'
                confidence = min(last_adx / 40, 1.0)
            else:
                regime = 'RANGING'
                confidence = 1 - (last_adx / 25)
            
            MARKET_REGIME['current'] = regime
            MARKET_REGIME['confidence'] = confidence
            
            logger.info(f"🌐 Market Regime: {regime} (Confidence: {confidence:.0%})")
            
            return {'regime': regime, 'confidence': confidence}
            
        except Exception as e:
            logger.error(f"Regime detection hatası: {e}")
            return None

# ==========================================
# ML MARKET SCANNER
# ==========================================
def market_scanner():
    """ML destekli piyasa tarayıcı"""
    logger.info("🤖 ML piyasa taraması başladı...")
    
    predictions = []
    
    for symbol in SYMBOLS:
        try:
            pred = MLPredictor.predict(symbol)
            
            if pred and pred['confidence'] > 70:
                predictions.append(pred)
                logger.info(f"🎯 ML Tahmin: {symbol} → {pred.get('direction', 'YUKARI')} (Güven: {pred['confidence']:.1f}%)")
                
                # Yönetici Bot (AutoTrader) - Sadece yüksek güven (>= 80) için işleme gir
                if pred['confidence'] >= 80:
                    try:
                        ticker = exchange.fetch_ticker(symbol)
                        current_price = ticker['last']
                        AutoTrader.execute_trade(symbol, current_price, pred, is_margin=True) # ML tahmini marjin/risk denenebilir
                    except Exception as e:
                        logger.error(f"AutoTrader Tetikleme Hatası (ML): {e}")
            
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"ML tarama hatası ({symbol}): {e}")
            continue
    
    # En güvenli tahminleri Telegram'a gönder
    if predictions:
        top_predictions = sorted(predictions, key=lambda x: x['confidence'], reverse=True)[:3]
        
        for pred in top_predictions:
            direction = pred.get('direction', 'YUKARI')
            emoji = '📈' if direction == 'YUKARI' else '📉'
            
            msg = f"🎯 **SİNYAL!**\n"
            msg += f"💎 **{pred['symbol']}** - {direction} {emoji}\n"
            if 'price' in pred:
                msg += f"💰 ${pred['price']:.4f}\n"
            msg += f"⭐ Güven: %{pred['confidence']:.1f}\n"
            msg += f"🎯 Model Acc: %{pred.get('accuracy', 0)*100:.1f}\n\n"
            
            msg += "🔍 Sinyaller:\n"
            
            # Sinyal nedenleri (Teknik veriler)
            for r in pred.get('reasons', []):
                msg += f"• {r}\n"
            
            # Risk faktörlerini de sinyal olarak ekleyelim veya ayrı gösterelim
            if pred.get('risks'):
                for r in pred['risks']:
                    msg += f"• {r}\n"
            
            # Hashtag ekle
            coin_name = pred['symbol'].split('/')[0]
            msg += f"\n#{coin_name} #Kripto #Sinyal #Trading\n"
            msg += f"👉 Ücretsiz VIP Sinyaller İçin Katıl: {TELEGRAM_CHANNEL_LINK}\n"
            
            safe_send_message(TELEGRAM_CHAT_ID, msg)
            time.sleep(0.5)
    
    logger.info(f"✅ ML taraması tamamlandı. {len(predictions)} tahmin yapıldı.")

# ==========================================
# DAILY REPORT
# ==========================================
def daily_report():
    """Günlük rapor"""
    logger.info("📊 Günlük rapor hazırlanıyor...")
    
    try:
        msg = "📊 **GÜNLÜK RAPOR**\n"
        msg += f"📅 {datetime.now().strftime('%d.%m.%Y')}\n\n"
        
        # Portfolio stats
        stats = PortfolioTracker.get_stats()
        if stats:
            msg += "💼 **PORTFÖY**\n"
            msg += f"• Toplam Trade: {stats['total_trades']}\n"
            msg += f"• Win Rate: {stats['win_rate']:.1f}%\n"
            msg += f"• Net PnL: {stats['total_pnl']:+.2f}%\n"
            msg += f"• Sharpe: {stats['sharpe']:.2f}\n\n"
        
        # Active positions
        if ACTIVE_POSITIONS:
            msg += f"📍 **AKTİF POZİSYONLAR: {len(ACTIVE_POSITIONS)}**\n"
            for symbol, pos in list(ACTIVE_POSITIONS.items())[:5]:
                msg += f"• {symbol}: {pos.get('pnl_pct', 0):+.2f}%\n"
            msg += "\n"
        
        # Market regime
        if MARKET_REGIME['current'] != 'UNKNOWN':
            msg += f"🌐 **PİYASA REJİMİ**\n"
            msg += f"• {MARKET_REGIME['current']} ({MARKET_REGIME['confidence']:.0%})\n\n"
        
        # Recent signals
        recent_signals = [s for s in SIGNAL_HISTORY if (datetime.now() - datetime.fromisoformat(s['timestamp'])).total_seconds() < 86400]
        if recent_signals:
            msg += f"🎯 **BUGÜNKÜ SİNYALLER: {len(recent_signals)}**\n"
            for sig in recent_signals[:3]:
                msg += f"• {sig['symbol']}: {sig['type']} ({sig['confidence']}%)\n"
        
        safe_send_message(TELEGRAM_CHAT_ID, msg)
        logger.info("✅ Günlük rapor gönderildi")
        
    except Exception as e:
        logger.error(f"Günlük rapor hatası: {e}")

# ==========================================
# OTOMATİK RAPORLAR (ZAMANLANMIŞ)
# ==========================================
def auto_hmap_report():
    """Her akşam 20:00 Heatmap gönderimi"""
    try:
        logger.info("🗺️ Otomatik hmap raporu gönderiliyor...")
        if not SYMBOLS: return
        
        tickers = exchange.fetch_tickers(SYMBOLS)
        symbols_data = []
        for symbol, ticker in tickers.items():
            if ticker['percentage'] is not None and ticker['quoteVolume'] is not None:
                symbols_data.append({
                    'symbol': symbol.split('/')[0],
                    'price': ticker['last'],
                    'change': ticker['percentage'],
                    'volume': ticker['quoteVolume']
                })
        
        heatmap_file = ChartGenerator.create_market_heatmap(symbols_data)
        if heatmap_file:
            with open(heatmap_file, 'rb') as photo:
                bot.send_photo(TELEGRAM_CHAT_ID, photo, caption="🗺️ **GÜNLÜK PİYASA HARİTASI (OTOMATİK)**\n\nKutu büyüklüğü hacmi, renk değişimi temsil eder.\n🟢 Yükseliş | 🔴 Düşüş", parse_mode="Markdown")
            try: os.remove(heatmap_file)
            except: pass
    except Exception as e:
        logger.error(f"Auto hmap hatası: {e}")

def auto_best_report():
    """Her akşam 20:45 En iyiler gönderimi"""
    try:
        logger.info("🚀 Otomatik best raporu gönderiliyor...")
        if not SYMBOLS: return
        
        tickers = exchange.fetch_tickers(SYMBOLS)
        data = []
        for symbol, ticker in tickers.items():
            if ticker['percentage'] is not None:
                data.append({'symbol': symbol.split('/')[0], 'change': ticker['percentage'], 'price': ticker['last']})
        
        top_5 = sorted(data, key=lambda x: x['change'], reverse=True)[:5]
        msg = "🚀 **GÜNÜN EN ÇOK YÜKSELENLERİ (20:45)**\n\n"
        for i, coin in enumerate(top_5, 1):
            msg += f"{i}. **{coin['symbol']}**: %{coin['change']:+.2f} (${coin['price']})\n"
        
        safe_send_message(TELEGRAM_CHAT_ID, msg)
    except Exception as e:
        logger.error(f"Auto best hatası: {e}")

def auto_worst_report():
    """Her akşam 21:00 En kötüler gönderimi"""
    try:
        logger.info("📉 Otomatik worst raporu gönderiliyor...")
        if not SYMBOLS: return
        
        tickers = exchange.fetch_tickers(SYMBOLS)
        data = []
        for symbol, ticker in tickers.items():
            if ticker['percentage'] is not None:
                data.append({'symbol': symbol.split('/')[0], 'change': ticker['percentage'], 'price': ticker['last']})
        
        worst_5 = sorted(data, key=lambda x: x['change'])[:5]
        msg = "📉 **GÜNÜN EN ÇOK DÜŞENLERİ (21:00)**\n\n"
        for i, coin in enumerate(worst_5, 1):
            msg += f"{i}. **{coin['symbol']}**: %{coin['change']:+.2f} (${coin['price']})\n"
        
        safe_send_message(TELEGRAM_CHAT_ID, msg)
    except Exception as e:
        logger.error(f"Auto worst hatası: {e}")

def scheduled_vip_report():
    """Zamanlanmış VIP VIP Raporu (BTC, XRP, BNB, AVAX, SOL + Heatmap)"""
    try:
        logger.info("💎 Zamanlanmış VIP Raporu hazırlanıyor...")
        
        # 1. Heatmap Hazırla
        tickers = exchange.fetch_tickers(SYMBOLS)
        symbols_data = []
        for symbol, ticker in tickers.items():
            if ticker['percentage'] is not None and ticker['quoteVolume'] is not None:
                symbols_data.append({
                    'symbol': symbol.split('/')[0],
                    'price': ticker['last'],
                    'change': ticker['percentage'],
                    'volume': ticker['quoteVolume']
                })
        heatmap_file = ChartGenerator.create_market_heatmap(symbols_data)
        
        # 2. Ana Coinlerin Analizlerini Topla
        report_msg = "🌟 **GÜNLÜK VIP MARKET ANALİZİ** 🌟\n\n"
        report_msg += "📊 **Piyasa Özeti & Liq Heatmap Analizi:**\n"
        
        # AI'dan piyasa özeti iste
        if GEMINI_API_KEY:
            try:
                prompt = f"Sen VIP bir kripto analistisin. Şu anki piyasa durumu için kısa, tweet tarzında, kışkırtıcı ve profesyonel bir özet yaz. Likidite bölgelerine ve hacim artışlarına değin. Maks 3 cümle. İsim kullanma."
                response = client.models.generate_content(model=GEN_MODEL, contents=prompt)
                report_msg += f"_{response.text.strip()}_\n\n"
            except:
                report_msg += "Piyasa genelinde hacimli hareketler gözleniyor, likidite bölgeleri test ediliyor. 👀\n\n"
        
        report_msg += "🚀 **Ana Coinler Görünüm:**\n"
        coin_charts = []
        for sym in VIP_SYMBOLS:
            try:
                bars = exchange.fetch_ohlcv(sym, '1h', limit=100)
                df = pd.DataFrame(bars, columns=['timestamp','open','high','low','close','volume'])
                df = calculate_indicators(df)
                last = df.iloc[-1]
                change = ((last['close'] - df.iloc[-24]['close']) / df.iloc[-24]['close'] * 100) if len(df) > 24 else 0
                
                report_msg += f"• **{sym.split('/')[0]}**: ${last['close']:.2f} (%{change:+.2f})\n"
                chart_file = ChartGenerator.create_candlestick_chart(sym, df)
                if chart_file: coin_charts.append((sym, chart_file))
            except: continue
        
        report_msg += f"\n👉 {TELEGRAM_CHANNEL_LINK}\n#BTC #Crypto #MarketReport #VIP"
        
        # 3. Gönderim - Kanala
        if heatmap_file:
            with open(heatmap_file, 'rb') as photo:
                bot.send_photo(TELEGRAM_CHAT_ID, photo, caption=report_msg, parse_mode="Markdown")
        else:
            safe_send_message(TELEGRAM_CHAT_ID, report_msg)
            
        # 4. Gönderim - Özelden (Kaan'a)
        if VIP_USER_ID:
            safe_send_message(VIP_USER_ID, "📝 **TWEETLENEBİLİR VIP RAPOR HAZIR!**")
            if heatmap_file:
                with open(heatmap_file, 'rb') as photo:
                    bot.send_photo(VIP_USER_ID, photo, caption=report_msg, parse_mode="Markdown")
            
            for sym, chart in coin_charts:
                with open(chart, 'rb') as photo:
                    bot.send_photo(VIP_USER_ID, photo, caption=f"📈 {sym} VIP Analiz Görünümü")
                time.sleep(1)
        
        # Temizlik
        if heatmap_file: 
            try: os.remove(heatmap_file)
            except: pass
        for _, chart in coin_charts:
            try: os.remove(chart)
            except: pass
            
    except Exception as e:
        logger.error(f"VIP Report hatası: {e}")

# ==========================================
# TELEGRAM KOMUTLARI (GELIŞTIRILMIŞ UI)
# ==========================================

# Ana menü
def create_main_menu():
    """Ana menü klavyesi"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📊 Portföy"),
        types.KeyboardButton("🎯 Sinyaller"),
        types.KeyboardButton("📈 Grafikler"),
        types.KeyboardButton("🤖 ML Tahmin"),
        types.KeyboardButton("⚙️ Ayarlar"),
        types.KeyboardButton("📋 Coin Listesi"),
        types.KeyboardButton("❓ Yardım")
    )
    return markup

@bot.message_handler(commands=['start', 'help'])
def start_command(message):
    """Hoşgeldin mesajı"""
    global VIP_USER_ID
    VIP_USER_ID = str(message.chat.id) # Gelen kullanıcının ID'sini kaydet
    logger.info(f"👤 VIP Kullanıcı ID tanımlandı: {VIP_USER_ID}")
    
    msg = "🚀 **ULTIMATE CRYPTO BOT**\n\n"
    msg += "✨ **Özellikler:**\n"
    msg += "• 📊 Portföy Takibi (Stop/Loss, Take Profit)\n"
    msg += "• 🎯 Teknik Sinyal Taraması\n"
    msg += "• 🤖 ML Tahmin Sistemi\n"
    msg += "• 📈 İnteraktif Grafikler\n"
    msg += "• 🔍 Order Book Analizi\n"
    msg += "• 💼 Risk Yönetimi\n"
    msg += "• 🧪 Backtest Sistemi\n\n"
    msg += "👇 **Hızlı Komutlar:**\n"
    msg += "/p - Portföy durumu\n"
    msg += "/signals - Aktif sinyaller\n"
    msg += "/chart btc - BTC grafiği\n"
    msg += "/predict eth - ETH ML tahmini\n"
    msg += "/risk - Risk ayarları\n\n"
    msg += "💡 Daha fazla bilgi için /menu kullanın!"
    
    bot.reply_to(message, msg, parse_mode="Markdown", reply_markup=create_main_menu())

@bot.message_handler(commands=['menu'])
def menu_command(message):
    """Ana menü"""
    bot.send_message(message.chat.id, "📋 Ana Menü", reply_markup=create_main_menu())

# Portföy komutları
@bot.message_handler(func=lambda m: m.text == "📊 Portföy")
@bot.message_handler(commands=['portfolio', 'p'])
def portfolio_command(message):
    """Portföy durumu"""
    try:
        stats = PortfolioTracker.get_stats()
        
        msg = "💼 **PORTFÖY DURUMU**\n\n"
        
        if stats:
            msg += f"📊 **İSTATİSTİKLER**\n"
            msg += f"• Toplam Trade: {stats['total_trades']}\n"
            msg += f"• Kazanan: {stats['wins']} ✅\n"
            msg += f"• Kaybeden: {stats['losses']} ❌\n"
            msg += f"• Win Rate: {stats['win_rate']:.1f}%\n"
            msg += f"• Ortalama Kazanç: +{stats['avg_win']:.2f}%\n"
            msg += f"• Ortalama Kayıp: {stats['avg_loss']:.2f}%\n"
            msg += f"• Risk/Reward: {stats.get('risk_reward', 0):.2f}\n"
            msg += f"• Net PnL: **{stats['total_pnl']:+.2f}%**\n"
            msg += f"• Sharpe Ratio: {stats['sharpe']:.2f}\n"
            msg += f"• Max Drawdown: {stats.get('max_drawdown', 0):.2f}%\n"
            msg += f"• Ort. Trade Süresi: {stats['avg_duration']:.1f} saat\n\n"
        
        if ACTIVE_POSITIONS:
            msg += f"📍 **AKTİF POZİSYONLAR ({len(ACTIVE_POSITIONS)})**\n"
            for symbol, pos in ACTIVE_POSITIONS.items():
                pnl = pos.get('pnl_pct', 0)
                emoji = '🟢' if pnl > 0 else '🔴' if pnl < 0 else '⚪'
                msg += f"{emoji} {symbol}\n"
                msg += f"   Giriş: ${pos['entry_price']:.2f}\n"
                msg += f"   Şu an: ${pos.get('current_price', 0):.2f}\n"
                msg += f"   PnL: {pnl:+.2f}%\n"
                msg += f"   Stop: ${pos.get('stop_loss', 0):.2f}\n"
                msg += f"   TP: ${pos.get('take_profit', 0):.2f}\n\n"
        else:
            msg += "📍 Aktif pozisyon yok\n\n"
        
        # Portfolio grafiği oluştur
        # Manuel Portföy Ekleme
        manual_pos = Database.get_manual_positions()
        if manual_pos:
            msg += "\n💼 **MANUEL PORTFÖY**\n"
            total_manual_pnl = 0
            
            for pos in manual_pos:
                try:
                    ticker = exchange.fetch_ticker(pos['symbol'])
                    curr_price = ticker['last']
                    value = pos['amount'] * curr_price
                    cost = pos['amount'] * pos['avg_price']
                    pnl = value - cost
                    pnl_pct = (pnl / cost) * 100
                    total_manual_pnl += pnl
                    
                    emoji = '🟢' if pnl >= 0 else '🔴'
                    msg += f"{emoji} **{pos['symbol']}**\n"
                    msg += f"   Miktar: {pos['amount']} | Ort: ${pos['avg_price']:.2f}\n"
                    msg += f"   Değer: ${value:.2f} ({pnl_pct:+.2f}%)\n"
                except:
                    msg += f"⚠️ {pos['symbol']} verisi alınamadı\n"
            
            msg += f"\n💰 **Manuel Toplam PnL:** ${total_manual_pnl:+.2f}\n"

        msg += "\nℹ️ Ekleme: `/ekle BTC 0.5 45000`\n"
        msg += "ℹ️ Silme: `/sil BTC`"
        
        # Portfolio grafiği
        chart_file = ChartGenerator.create_portfolio_chart()
        
        bot.reply_to(message, msg, parse_mode="Markdown")
        
        if chart_file:
            try:
                with open(chart_file, 'rb') as photo:
                    bot.send_photo(message.chat.id, photo, caption="📈 Portföy Performansı")
            except:
                pass
        
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

# Manuel ekleme komutu
@bot.message_handler(commands=['ekle', 'add'])
def add_portfolio_command(message):
    """Manuel coin ekle"""
    try:
        parts = message.text.split()
        if len(parts) < 4:
            bot.reply_to(message, "⚠️ Kullanım: `/ekle BTC 0.5 45000` (Coin Miktar Fiyat)")
            return
        
        coin = parts[1].upper()
        if "/USDT" not in coin: coin += "/USDT"
        
        amount = float(parts[2])
        price = float(parts[3])
        
        Database.add_manual_position(coin, amount, price)
        bot.reply_to(message, f"✅ **{coin}** portföye eklendi.\n📦 Miktar: {amount}\n💰 Fiyat: ${price}")
        
    except ValueError:
        bot.reply_to(message, "❌ Hatalı sayı formatı!")
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

# Manuel silme komutu
@bot.message_handler(commands=['sil', 'remove'])
def remove_portfolio_command(message):
    """Manuel coin sil"""
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "⚠️ Kullanım: `/sil BTC`")
            return
        
        coin = parts[1].upper()
        if "/USDT" not in coin: coin += "/USDT"
        
        Database.delete_manual_position(coin)
        bot.reply_to(message, f"🗑️ **{coin}** portföyden silindi.")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

# Sinyal komutları
@bot.message_handler(func=lambda m: m.text == "🎯 Sinyaller")
@bot.message_handler(commands=['signals', 's'])
def signals_command(message):
    """Son sinyaller"""
    try:
        # Eğer hafıza boşsa veritabanından yüklemeyi dene
        history = SIGNAL_HISTORY
        if not history:
            history = Database.get_recent_signals(limit=10)
            
        if not history:
            bot.reply_to(message, "Henüz sinyal yok veya veritabanı boş.")
            return
        
        # Son 24 saati göster (önceden 1 saatti)
        recent = [s for s in history if (datetime.now() - datetime.fromisoformat(s['timestamp'])).total_seconds() < 86400]
        
        if not recent:
            # Zaman filtresine takıldıysa en son 5'i göster
            recent = history[-5:]
        
        if not recent:
            bot.reply_to(message, "Son 1 saatte sinyal yok.")
            return
        
        msg = "🎯 **SON SİNYALLER**\n\n"
        
        markup = types.InlineKeyboardMarkup()
        unique_coins = set()
        
        for sig in recent[:10]:
            emoji = '🟢' if sig['type'] == 'BUY' else '🔴'
            msg += f"{emoji} **{sig['symbol']}** - {sig['type']}\n"
            msg += f"💰 Fiyat: ${sig['price']:.2f}\n"
            msg += f"🎯 Güven: {sig['confidence']}%\n"
            msg += f"📊 Sinyaller: {sig['reason']}\n"
            time_ago = (datetime.now() - datetime.fromisoformat(sig['timestamp'])).total_seconds() / 60
            msg += f"⏰ {time_ago:.0f} dakika önce\n\n"
            
            coin = sig['symbol']
            if coin not in unique_coins:
                markup.add(types.InlineKeyboardButton(f"🐦 Tweet Oluştur: {coin}", callback_data=f"tweet_{coin}"))
                unique_coins.add(coin)
        
        bot.reply_to(message, msg, parse_mode="Markdown", reply_markup=markup)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

# Grafik komutları
@bot.message_handler(func=lambda m: m.text == "📈 Grafikler")
@bot.message_handler(commands=['chart'])
def chart_command(message):
    """Grafik oluştur"""
    try:
        parts = message.text.split()
        
        if len(parts) < 2 and message.text != "📈 Grafikler":
            bot.reply_to(message, "Kullanım: `/chart btc` veya '📈 Grafikler' butonuna basın", parse_mode="Markdown")
            return
        
        if message.text == "📈 Grafikler":
            # Inline keyboard ile coin seçimi
            markup = types.InlineKeyboardMarkup(row_width=3)
            buttons = [types.InlineKeyboardButton(coin.split('/')[0], callback_data=f"chart_{coin}") for coin in SYMBOLS[:9]]
            markup.add(*buttons)
            bot.send_message(message.chat.id, "📊 Hangi coinin grafiğini görmek istersiniz?", reply_markup=markup)
            return
        
        coin = parts[1].upper()
        if "/USDT" not in coin:
            coin += "/USDT"
        
        if coin not in SYMBOLS:
            bot.reply_to(message, f"❌ {coin} listede yok")
            return
        
        bot.reply_to(message, f"📊 {coin} grafiği oluşturuluyor...")
        
        # Veri çek
        bars = exchange.fetch_ohlcv(coin, '1h', limit=200)
        df = pd.DataFrame(bars, columns=['timestamp','open','high','low','close','volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp')
        df = calculate_indicators(df)
        
        # Son sinyalleri ekle
        recent_signals = [s for s in SIGNAL_HISTORY if s['symbol'] == coin][-5:]
        signals = []
        for sig in recent_signals:
            signals.append({
                'type': sig['type'],
                'price': sig['price'],
                'time': datetime.fromisoformat(sig['timestamp'])
            })
        
        # Grafik oluştur
        chart_file = ChartGenerator.create_candlestick_chart(coin, df, signals)
        
        # Tweet Butonu
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🐦 Tweet Analizi Oku", callback_data=f"tweet_{coin}"))
        
        if chart_file:
            with open(chart_file, 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption=f"📈 {coin} Teknik Analiz", reply_markup=markup)
        else:
            bot.reply_to(message, "❌ Grafik oluşturulamadı")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

# Chart callback handler
@bot.callback_query_handler(func=lambda call: call.data.startswith('chart_'))
def chart_callback(call):
    """Grafik callback"""
    coin = call.data.replace('chart_', '')
    
    try:
        bot.answer_callback_query(call.id, f"{coin} grafiği hazırlanıyor...")
        bot.send_message(call.message.chat.id, f"📊 {coin} grafiği oluşturuluyor...")
        
        # Veri çek
        bars = exchange.fetch_ohlcv(coin, '1h', limit=200)
        df = pd.DataFrame(bars, columns=['timestamp','open','high','low','close','volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp')
        df = calculate_indicators(df)
        
        # Grafik oluştur
        chart_file = ChartGenerator.create_candlestick_chart(coin, df)
        
        # Tweet Butonu
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🐦 Tweet Analizi Oku", callback_data=f"tweet_{coin}"))
        
        if chart_file:
            with open(chart_file, 'rb') as photo:
                bot.send_photo(call.message.chat.id, photo, caption=f"📈 {coin} Teknik Analiz", reply_markup=markup)
        
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Hata: {str(e)}")

# Tweet callback handler
@bot.callback_query_handler(func=lambda call: call.data.startswith('tweet_'))
def tweet_callback(call):
    """Tweet analizi oluştur"""
    coin = call.data.replace('tweet_', '')
    
    try:
        bot.answer_callback_query(call.id, "🐦 Tweet hazırlanıyor...")
        bot.send_chat_action(call.message.chat.id, 'typing')
        
        # Veri çek
        bars = exchange.fetch_ohlcv(coin, '1h', limit=100)
        df = pd.DataFrame(bars, columns=['timestamp','open','high','low','close','volume'])
        df = calculate_indicators(df)
        
        # Tweet üret
        tweet_text = TweetGenerator.generate_tweet(coin, df)
        
        # Mesaj olarak gönder (Kopyalanabilir format) -> Telegram Özel'den kullanıcıya at
        bot.send_message(call.from_user.id, tweet_text)
        bot.answer_callback_query(call.id, "Tweet özelden (bota) iletildi! 🚀")
        
    except Exception as e:
        try:
            bot.send_message(call.from_user.id, f"❌ Analiz oluşturulamadı: {str(e)}")
        except:
            bot.send_message(call.message.chat.id, f"❌ Bot ile özel mesajlaşmanızı başlatmanız gerekiyor.")


# ML Tahmin
@bot.message_handler(func=lambda m: m.text == "🤖 ML Tahmin")
@bot.message_handler(commands=['predict'])
def predict_command(message):
    """ML tahmin"""
    try:
        parts = message.text.split()
        
        if len(parts) < 2 and message.text != "🤖 ML Tahmin":
            bot.reply_to(message, "Kullanım: `/predict btc` veya '🤖 ML Tahmin' butonuna basın", parse_mode="Markdown")
            return
        
        if message.text == "🤖 ML Tahmin":
            # Inline keyboard
            markup = types.InlineKeyboardMarkup(row_width=3)
            buttons = [types.InlineKeyboardButton(coin.split('/')[0], callback_data=f"predict_{coin}") for coin in SYMBOLS[:9]]
            markup.add(*buttons)
            bot.send_message(message.chat.id, "🤖 Hangi coin için ML tahmini?", reply_markup=markup)
            return
        
        coin = parts[1].upper()
        if "/USDT" not in coin:
            coin += "/USDT"
        
        bot.reply_to(message, f"🤖 {coin} ML tahmini yapılıyor...")
        
        pred = MLPredictor.predict(coin)
        
        if not pred:
            bot.reply_to(message, "❌ Tahmin başarısız")
            return
        
        emoji = '📈' if pred['direction'] == 'YUKARI' else '📉'
        msg = f"🎯 **SİNYAL (ML): {coin}**\n\n"
        msg += f"💎 **Yön:** {pred['direction']} {emoji}\n"
        if 'price' in pred:
            msg += f"💰 **Son Fiyat:** ${pred['price']:.4f}\n"
        msg += f"⭐ **Güven:** %{pred['confidence']:.1f}\n"
        msg += f"🎯 **Model Doğruluğu:** %{pred['accuracy']*100:.1f}\n\n"
        
        # Nedenler
        if pred['reasons']:
            msg += "🗝️ **ANA NEDENLER:**\n"
            for r in pred['reasons']:
                msg += f"• {r}\n"
        
        # Riskler
        if pred.get('risks'):
            msg += "\n⚠️ **RİSK FAKTÖRLERİ:**\n"
            for r in pred['risks']:
                msg += f"• {r}\n"
        
        # Teknik Özet
        if pred.get('technical'):
            tech = pred['technical']
            msg += "\n📈 **TEKNİK ÖZET:**\n"
            msg += f"• RSI: {tech['rsi']:.1f} ({'Sıcak' if tech['rsi']>60 else 'Soğuk' if tech['rsi']<40 else 'Nötr'})\n"
            msg += f"• ADX: {tech['adx']:.1f} ({'Güçlü' if tech['adx']>25 else 'Zayıf'})\n"
            msg += f"• Hacim: {tech['vol_ratio']:.1f}x ({'Yüksek' if tech['vol_ratio']>1.5 else 'Düşük'})\n"
            msg += f"• EMA Farkı: %{tech['ema_diff']:+.1f}\n"

        if pred['confidence'] > 85:
            msg += "\n✅ **Yüksek Güvenilirlik!** (Sniper Mode Uygun)\n"
        elif pred['confidence'] > 65:
            msg += "\n⚠️ **Orta Güvenilirlik**\n"
        else:
            msg += "\n❌ **Düşük Güvenilirlik** - İşlem Önerilmez\n"
            
        coin_name = pred['symbol'].split('/')[0]
        msg += f"\n#{coin_name} #Kripto #Sinyal #Trading\n"
        msg += f"👉 Ücretsiz VIP Sinyaller İçin Katıl: {TELEGRAM_CHANNEL_LINK}\n"
        
        bot.reply_to(message, msg, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

# Predict callback
@bot.callback_query_handler(func=lambda call: call.data.startswith('predict_'))
def predict_callback(call):
    """ML tahmin callback"""
    coin = call.data.replace('predict_', '')
    
    try:
        bot.answer_callback_query(call.id, f"{coin} ML tahmini yapılıyor...")
        
        pred = MLPredictor.predict(coin)
        
        if not pred:
            bot.send_message(call.message.chat.id, "❌ Tahmin başarısız")
            return
        
        emoji = '📈' if pred['direction'] == 'YUKARI' else '📉'
        msg = f"🎯 **SİNYAL (ML): {coin}**\n\n"
        msg += f"💎 **Yön:** {pred['direction']} {emoji}\n"
        if 'price' in pred:
            msg += f"💰 **Son Fiyat:** ${pred['price']:.4f}\n"
        msg += f"⭐ **Güven:** %{pred['confidence']:.1f}\n"
        msg += f"🎯 **Model Doğruluğu:** %{pred['accuracy']*100:.1f}\n\n"
        
        if pred['reasons']:
            msg += "🗝️ **ANA NEDENLER:**\n"
            for r in pred['reasons']:
                msg += f"• {r}\n"
                
        if pred.get('risks'):
            msg += "\n⚠️ **RİSK FAKTÖRLERİ:**\n"
            for r in pred['risks']:
                msg += f"• {r}\n"
                
        coin_name = pred['symbol'].split('/')[0]
        msg += f"\n#{coin_name} #Kripto #Sinyal #Trading\n"
        msg += f"👉 Ücretsiz VIP Sinyaller İçin Katıl: {TELEGRAM_CHANNEL_LINK}\n"
        
        bot.send_message(call.message.chat.id, msg, parse_mode="Markdown")
        
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Hata: {str(e)}")



# Ayarlar
@bot.message_handler(func=lambda m: m.text == "⚙️ Ayarlar")
@bot.message_handler(commands=['settings', 'risk'])
def settings_command(message):
    """Risk ayarları"""
    msg = "⚙️ **RİSK AYARLARI**\n\n"
    msg += f"💼 Max Pozisyon: {RISK_SETTINGS['max_position_size']}%\n"
    msg += f"📉 Max Drawdown: {RISK_SETTINGS['max_drawdown']}%\n"
    msg += f"🛑 Default Stop Loss: {RISK_SETTINGS['default_stop_loss']}%\n"
    msg += f"🎯 Default Take Profit: {RISK_SETTINGS['default_take_profit']}%\n"
    msg += f"🔢 Max Eşzamanlı Trade: {RISK_SETTINGS['max_concurrent_trades']}\n"
    msg += f"💰 Risk/Trade: {RISK_SETTINGS['risk_per_trade']}%\n\n"
    msg += "Ayarları değiştirmek için: `/setrisk <parametre> <değer>`\n"
    msg += "Örnek: `/setrisk stop_loss 5`"
    
    bot.reply_to(message, msg, parse_mode="Markdown")

@bot.message_handler(commands=['setrisk'])
def setrisk_command(message):
    """Risk ayarlarını değiştir"""
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message, "Kullanım: `/setrisk <parametre> <değer>`\nÖrnek: `/setrisk stop_loss 5`", parse_mode="Markdown")
            return
        
        param = parts[1].lower()
        value = float(parts[2])
        
        valid_params = {
            'stop_loss': 'default_stop_loss',
            'take_profit': 'default_take_profit',
            'max_position': 'max_position_size',
            'max_drawdown': 'max_drawdown',
            'risk_per_trade': 'risk_per_trade',
            'max_trades': 'max_concurrent_trades'
        }
        
        if param not in valid_params:
            bot.reply_to(message, f"❌ Geçersiz parametre. Geçerli parametreler: {', '.join(valid_params.keys())}")
            return
        
        RISK_SETTINGS[valid_params[param]] = value
        Database.set_setting(valid_params[param], value)
        
        bot.reply_to(message, f"✅ {param} = {value} olarak ayarlandı")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

# Coin listesi
@bot.message_handler(func=lambda m: m.text == "📋 Coin Listesi")
@bot.message_handler(commands=['liste', 'list'])
def liste_command(message):
    """Coin listesi"""
    if not SYMBOLS:
        bot.reply_to(message, "⚠️ Liste boş. Lütfen piyasa taraması bitene kadar bekleyin.")
        return
        
    msg = f"📋 **TAKİP EDİLEN COİNLER ({len(SYMBOLS)} Adet)**\n\n"
    
    # Çok uzun mesajları önlemek için virgülle ayırıp 50'li parçalara böl
    chunk_size = 50
    for i in range(0, len(SYMBOLS), chunk_size):
        chunk = SYMBOLS[i:i+chunk_size]
        text_chunk = ", ".join([c.replace('/USDT', '') for c in chunk])
        safe_send_message(message.chat.id, msg + text_chunk if i == 0 else text_chunk)
        
    safe_send_message(message.chat.id, "\n💡 Detaylı analiz için: `/predict COINADI`")

# 24 Saatlik En İyiler
@bot.message_handler(commands=['best'])
def best_command(message):
    """24h En iyi performans gösteren coinler"""
    try:
        if not SYMBOLS:
            bot.reply_to(message, "⚠️ Liste henüz hazır değil.")
            return
            
        bot.reply_to(message, "📊 24 saatlik veriler analiz ediliyor...")
        tickers = exchange.fetch_tickers(SYMBOLS)
        
        data = []
        for symbol, ticker in tickers.items():
            if ticker['percentage'] is not None:
                data.append({
                    'symbol': symbol.split('/')[0],
                    'change': ticker['percentage'],
                    'price': ticker['last']
                })
        
        top_5 = sorted(data, key=lambda x: x['change'], reverse=True)[:5]
        
        msg = "🚀 **24H EN ÇOK YÜKSELENLER**\n\n"
        for i, coin in enumerate(top_5, 1):
            msg += f"{i}. **{coin['symbol']}**: %{coin['change']:+.2f} (${coin['price']})\n"
            
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Best command hatası: {e}")
        bot.reply_to(message, "❌ Veriler alınırken bir hata oluştu.")

# 24 Saatlik En Kötüler
@bot.message_handler(commands=['worst'])
def worst_command(message):
    """24h En kötü performans gösteren coinler"""
    try:
        if not SYMBOLS:
            bot.reply_to(message, "⚠️ Liste henüz hazır değil.")
            return

        bot.reply_to(message, "📊 24 saatlik veriler analiz ediliyor...")
        tickers = exchange.fetch_tickers(SYMBOLS)
        
        data = []
        for symbol, ticker in tickers.items():
            if ticker['percentage'] is not None:
                data.append({
                    'symbol': symbol.split('/')[0],
                    'change': ticker['percentage'],
                    'price': ticker['last']
                })
        
        worst_5 = sorted(data, key=lambda x: x['change'])[:5]
        
        msg = "📉 **24H EN ÇOK DÜŞENLER**\n\n"
        for i, coin in enumerate(worst_5, 1):
            msg += f"{i}. **{coin['symbol']}**: %{coin['change']:+.2f} (${coin['price']})\n"
            
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Worst command hatası: {e}")
        bot.reply_to(message, "❌ Veriler alınırken bir hata oluştu.")

# Market Heatmap
@bot.message_handler(commands=['hmap'])
def hmap_command(message):
    """Piyasa Heatmap (Treemap)"""
    try:
        if not SYMBOLS:
            bot.reply_to(message, "⚠️ Liste henüz hazır değil.")
            return

        bot.reply_to(message, "🗺️ Piyasa haritası oluşturuluyor (Hacim & Değişim)...")
        tickers = exchange.fetch_tickers(SYMBOLS)
        
        symbols_data = []
        for symbol, ticker in tickers.items():
            if ticker['percentage'] is not None and ticker['quoteVolume'] is not None:
                symbols_data.append({
                    'symbol': symbol.split('/')[0],
                    'price': ticker['last'],
                    'change': ticker['percentage'],
                    'volume': ticker['quoteVolume']
                })
        
        heatmap_file = ChartGenerator.create_market_heatmap(symbols_data)
        
        if heatmap_file:
            with open(heatmap_file, 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption="🗺️ **Kripto Piyasa Haritası**\n\nKutu büyüklüğü 24 saatlik hacmi, renk ise fiyat değişimini temsil eder.\n🟢 Yükseliş | 🔴 Düşüş", parse_mode="Markdown")
            # Geçici dosyayı sil
            try: os.remove(heatmap_file)
            except: pass
        else:
            bot.reply_to(message, "❌ Harita oluşturulamadı.")
            
    except Exception as e:
        logger.error(f"Hmap command hatası: {e}")
        bot.reply_to(message, "❌ Harita verileri alınırken bir hata oluştu.")


@bot.message_handler(commands=['ekle', 'add'])
def ekle_command(message):
    """Coin ekle (İzleme veya Portföy)"""
    try:
        parts = message.text.split()
        
        # Kullanım 1: İzleme Listesi (/ekle BTC)
        if len(parts) == 2:
            coin = parts[1].upper()
            if "/USDT" not in coin: coin += "/USDT"
            
            if coin in SYMBOLS:
                bot.reply_to(message, f"ℹ️ {coin} zaten izleme listesinde.")
            else:
                SYMBOLS.append(coin)
                bot.reply_to(message, f"✅ {coin} izleme listesine eklendi! ML modeli eğitiliyor...")
                MLPredictor.train_model(coin)
                
        # Kullanım 2: Portföy (/ekle BTC 0.5 45000)
        elif len(parts) == 4:
            coin = parts[1].upper()
            if "/USDT" not in coin: coin += "/USDT"
            
            try:
                amount = float(parts[2])
                cost = float(parts[3])
                
                MANUAL_PORTFOLIO[coin] = {
                    'amount': amount,
                    'cost': cost,
                    'date': str(datetime.now())
                }
                bot.reply_to(message, f"💼 Portföye eklendi: {coin}\nMiktar: {amount}\nMaliyet: ${cost}")
            except ValueError:
                bot.reply_to(message, "❌ Hata: Miktar ve maliyet sayı olmalı!\nÖrn: `/ekle BTC 0.5 45000`")
                
        else:
            bot.reply_to(message, "ℹ️ Kullanım:\n👉 İzleme: `/ekle BTC`\n👉 Portföy: `/ekle BTC 0.5 45000`", parse_mode="Markdown")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

@bot.message_handler(commands=['sil', 'remove'])
def sil_command(message):
    """Coin sil"""
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Kullanım: `/sil BTC`", parse_mode="Markdown")
            return
        
        coin = parts[1].upper()
        if "/USDT" not in coin: coin += "/USDT"
        
        deleted = []
        
        # Portföyden sil
        if coin in MANUAL_PORTFOLIO:
            del MANUAL_PORTFOLIO[coin]
            deleted.append("Portföy")
            
        # İzleme listesinden sil
        if coin in SYMBOLS:
            SYMBOLS.remove(coin)
            deleted.append("İzleme Listesi")
            
        if deleted:
            bot.reply_to(message, f"✅ {coin} şuradan silindi: {', '.join(deleted)}")
        else:
            bot.reply_to(message, f"❌ {coin} bulunamadı.")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

@bot.message_handler(commands=['portfoy', 'portfolio', 'canta'])
def portfoy_command(message):
    """Portföy durumu"""
    try:
        msg = "💼 **PORTFÖY DURUMU**\n\n"
        total_pnl_usd = 0
        
        if not MANUAL_PORTFOLIO:
            msg += "📭 Portföy boş. Ekleme yapmak için:\n`/ekle BTC 0.1 45000`\n\n"
        else:
            msg += "**Manuel Yatırımlar:**\n"
            for symbol, data in MANUAL_PORTFOLIO.items():
                try:
                    ticker = exchange.fetch_ticker(symbol)
                    current_price = ticker['last']
                    
                    amount = data['amount']
                    cost = data['cost']
                    value = amount * current_price
                    initial_value = amount * cost
                    pnl = value - initial_value
                    pnl_pct = (pnl / initial_value) * 100
                    
                    total_pnl_usd += pnl
                    
                    icon = "🟢" if pnl >= 0 else "🔴"
                    msg += f"{icon} **{symbol}**\n"
                    msg += f"   Miktar: {amount} | Değer: ${value:.0f}\n"
                    msg += f"   Kâr/Zarar: ${pnl:.0f} (%{pnl_pct:.2f})\n\n"
                    
                except Exception as e:
                    msg += f"⚠️ {symbol}: Fiyat alınamadı\n"
        
        # Bot Pozisyonları (Paper)
        if AutoTrader.paper_positions:
            has_pos = False
            active_msg = "**🤖 Bot Pozisyonları:**\n"
            for symbol, data in AutoTrader.paper_positions.items():
                if data['position']:
                    has_pos = True
                    pos = data['position']
                    ticker = exchange.fetch_ticker(symbol)
                    curr = ticker['last']
                    entry = pos['entry_price']
                    pnl_pct = ((curr - entry) / entry) * 100
                    
                    active_msg += f"🤖 {symbol} ({pos['direction']})\n"
                    active_msg += f"   Giriş: ${entry} | Anlık: ${curr}\n"
                    active_msg += f"   PnL: %{pnl_pct:.2f}\n"
            
            if has_pos:
                msg += active_msg
        
        bot.reply_to(message, msg, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

# Yardım
@bot.message_handler(func=lambda m: m.text == "❓ Yardım")
def help_button(message):
    """Yardım"""
    start_command(message)

# Diğer komutlar
@bot.message_handler(commands=['backtest'])
def backtest_command(message):
    """Backtest"""
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Kullanım: `/backtest btc`", parse_mode="Markdown")
            return
        
        coin = parts[1].upper()
        if "/USDT" not in coin:
            coin += "/USDT"
        
        months = int(parts[2]) if len(parts) > 2 else 6
        
        bot.reply_to(message, f"🔄 Backtest başlatılıyor: {coin} ({months} ay)...")
        
        result = Backtester.run_backtest(coin, months)
        
        if not result:
            bot.reply_to(message, "❌ Backtest başarısız")
            return
        
        msg = f"📊 **BACKTEST: {coin}**\n\n"
        msg += f"📅 Süre: {months} ay\n"
        msg += f"📈 Toplam Trade: {result['total_trades']}\n"
        msg += f"✅ Kazanan: {result['wins']}\n"
        msg += f"❌ Kaybeden: {result['losses']}\n"
        msg += f"🎯 Win Rate: {result['win_rate']:.1f}%\n"
        msg += f"💚 Ortalama Kazanç: +{result['avg_win']:.2f}%\n"
        msg += f"💔 Ortalama Kayıp: {result['avg_loss']:.2f}%\n"
        msg += f"💰 Net PnL: {result['total_pnl']:+.2f}%\n"
        msg += f"💵 Final Sermaye: ${result['final_capital']:.2f}\n"
        msg += f"📊 Sharpe: {result['sharpe']:.2f}\n"
        
        bot.reply_to(message, msg, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

@bot.message_handler(commands=['stats'])
def stats_command(message):
    """Detaylı istatistikler"""
    portfolio_command(message)

@bot.message_handler(commands=['orderbook', 'ob'])
def orderbook_command(message):
    """Order book analizi"""
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Kullanım: `/orderbook btc`", parse_mode="Markdown")
            return
        
        coin = parts[1].upper()
        if "/USDT" not in coin:
            coin += "/USDT"
        
        ob = OrderBookAnalyzer.analyze_order_book(coin)
        
        if not ob:
            bot.reply_to(message, "❌ Order book analiz başarısız")
            return
        
        msg = f"📊 **ORDER BOOK: {coin}**\n\n"
        msg += f"⚖️ Bid/Ask Ratio: {ob['imbalance']:.2f}\n"
        msg += f"📈 Sentiment: **{ob['sentiment']}**\n\n"
        
        msg += f"🟢 **ALIŞ DUVARLARI:**\n"
        for bid in ob['big_bids']:
            msg += f"  ${bid['price']:.2f}: {bid['amount']:.2f}\n"
        
        msg += f"\n🔴 **SATIŞ DUVARLARI:**\n"
        for ask in ob['big_asks']:
            msg += f"  ${ask['price']:.2f}: {ask['amount']:.2f}\n"
        
        bot.reply_to(message, msg, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

@bot.message_handler(commands=['correlation', 'corr'])
def correlation_command(message):
    """Korelasyon matrisi"""
    try:
        bot.reply_to(message, "📊 Korelasyon matrisi oluşturuluyor...")
        
        chart_file = ChartGenerator.create_correlation_heatmap()
        
        if chart_file:
            with open(chart_file, 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption="📊 Coin Korelasyon Matrisi")
        else:
            bot.send_message(message.chat.id, "❌ Grafik oluşturulamadı")
        
        if CORRELATION_DATA.get('high_correlations'):
            msg = "🔗 **YÜKSEK KORELASYONLAR:**\n\n"
            for corr in CORRELATION_DATA['high_correlations'][:10]:
                msg += f"• {corr['pair']}: {corr['correlation']:.2f}\n"
            bot.send_message(message.chat.id, msg, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

@bot.message_handler(commands=['regime'])
def regime_command(message):
    """Market regime"""
    try:
        bot.reply_to(message, "🔄 Piyasa rejimi tespit ediliyor...")
        
        regime = MarketRegimeDetector.detect_regime()
        
        if not regime:
            bot.reply_to(message, "❌ Regime detection başarısız")
            return
        
        msg = f"🌐 **MARKET REGIME: BTC**\n\n"
        msg += f"📊 Mevcut: **{regime['regime']}**\n"
        msg += f"🎯 Güven: {regime['confidence']:.0%}\n\n"
        
        if regime['regime'] == 'TRENDING':
            msg += "📈 Piyasa trend halinde. Trend takip stratejileri uygun.\n"
        elif regime['regime'] == 'RANGING':
            msg += "↔️ Piyasa yatay. Mean reversion stratejileri uygun.\n"
        else:
            msg += "⚠️ Piyasa volatil. Dikkatli olun, pozisyon boyutlarını küçültün.\n"
        
        bot.reply_to(message, msg, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

@bot.message_handler(commands=['position', 'kelly'])
def position_command(message):
    """Position sizing"""
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Kullanım: `/position btc`", parse_mode="Markdown")
            return
        
        coin = parts[1].upper()
        if "/USDT" not in coin:
            coin += "/USDT"
        
        kelly = PositionSizer.calculate_kelly(coin)
        
        msg = f"💼 **POZİSYON BÜYÜKLÜĞÜ: {coin}**\n\n"
        
        if 'note' in kelly:
            msg += f"⚠️ {kelly['note']}\n"
        else:
            msg += f"📐 Kelly Criterion: {kelly['kelly']:.1f}%\n"
            msg += f"✅ Önerilen (Kelly×0.5): **{kelly['recommended']:.1f}%**\n\n"
            msg += f"📊 Win Rate: {kelly['win_rate']:.1f}%\n"
            msg += f"📈 Avg Win: +{kelly['avg_win']:.2f}%\n"
            msg += f"📉 Avg Loss: {kelly['avg_loss']:.2f}%\n"
            msg += f"🔢 Trade Sayısı: {kelly['trades']}\n"
        
        bot.reply_to(message, msg, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

@bot.message_handler(commands=['scan'])
def scan_command(message):
    """Manuel tarama"""
    bot.reply_to(message, "🔍 Tarama başlatılıyor...")
    professional_signal_scanner()

@bot.message_handler(commands=['mlscan'])
def mlscan_command(message):
    """ML tarama"""
    bot.reply_to(message, "🤖 ML taraması başlatılıyor...")
    market_scanner()

@bot.message_handler(commands=['report'])
def report_command(message):
    """Günlük rapor"""
    daily_report()

@bot.message_handler(commands=['autotrade'])
def autotrade_command(message):
    """Otomatik trade'i başlat"""
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "ℹ️ Kullanım: /autotrade BTC/USDT\nTüm coinler: /autotrade all")
            return
        
        target = parts[1].upper()
        if target == 'ALL':
            for symbol in SYMBOLS:
                AutoTrader.enable(symbol)
            bot.reply_to(message, f"🤖 Tüm coinler için paper trading aktif! ({len(SYMBOLS)} coin)")
        else:
            symbol = target if '/' in target else f"{target}/USDT"
            if symbol in SYMBOLS:
                AutoTrader.enable(symbol)
                bot.reply_to(message, f"🤖 {symbol} için paper trading aktif!")
            else:
                bot.reply_to(message, f"❌ {symbol} izleme listenizde yok.")
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {e}")

@bot.message_handler(commands=['autostop'])
def autostop_command(message):
    """Otomatik trade'i durdur"""
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "ℹ️ Kullanım: /autostop BTC/USDT\nTüm coinler: /autostop all")
            return
        
        target = parts[1].upper()
        if target == 'ALL':
            for symbol in list(AutoTrader.paper_positions.keys()):
                AutoTrader.disable(symbol)
            bot.reply_to(message, "⛔ Tüm paper trading durduruldu!")
        else:
            symbol = target if '/' in target else f"{target}/USDT"
            AutoTrader.disable(symbol)
            bot.reply_to(message, f"⛔ {symbol} paper trading durduruldu!")
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {e}")

# ==========================================
# İÇERİK STRATEJİSİ (KRİPTOGRAF)
# ==========================================
def sabah_gunluk_seri():
    """Sabah 08:00 KriptoGraf Günlük Serisi"""
    try:
        logger.info("🌅 Sabah Günlük Serisi hazırlanıyor...")
        safe_send_message(TELEGRAM_CHAT_ID, "🌅 **KriptoGraf Günlük Serisi Hazırlanıyor...**")
        
        # Hacim veya trend puanına göre en iyi 3 coin
        top_coins = []
        for symbol in SYMBOLS:
            try:
                bars = exchange.fetch_ohlcv(symbol, '1h', limit=50)
                df = pd.DataFrame(bars, columns=['timestamp','open','high','low','close','volume'])
                df = calculate_indicators(df)
                last = df.iloc[-1]
                score = last.get('vol_ratio', 1.0) * last.get('adx', 15)
                top_coins.append({'symbol': symbol, 'score': score, 'df': df})
            except:
                continue
                
        top_coins = sorted(top_coins, key=lambda x: x['score'], reverse=True)[:3]
        
        msg = "🌅 **KriptoGraf Günlük** 🌅\n*Bugünün İzlenecek 3 Altcoini*\n\n"
        for idx, item in enumerate(top_coins, 1):
            sym = item['symbol']
            df = item['df']
            last = df.iloc[-1]
            price = last['close']
            rsi = last.get('rsi', 50)
            
            recent_low = df['low'].rolling(20).min().iloc[-1]
            recent_high = df['high'].rolling(20).max().iloc[-1]
            target = recent_high * 1.05 if price > recent_low else recent_high
            
            msg += f"**{idx}. {sym.split('/')[0]}**\n"
            msg += f"💰 Fiyat: ${price:.3f}\n"
            msg += f"📊 RSI: {rsi:.1f} | 🎯 Hedef: ${target:.3f}\n\n"
            
        msg += "Analiz detayları grafiklerde olacak.\n"
        msg += f"👉 {TELEGRAM_CHANNEL_LINK}\n🔗 {LINKTREE_LINK}"
        
        safe_send_message(TELEGRAM_CHAT_ID, msg)
        
        # Grafikleri yolla
        for item in top_coins:
            chart_file = ChartGenerator.create_candlestick_chart(item['symbol'], item['df'])
            if chart_file:
                with open(chart_file, 'rb') as photo:
                    bot.send_photo(TELEGRAM_CHAT_ID, photo, caption=f"📈 {item['symbol']} Teknik Görünüm\n\n👉 {TELEGRAM_CHANNEL_LINK}")
                    
    except Exception as e:
        logger.error(f"Sabah serisi hatası: {e}")

def aksam_sinyal_serisi():
    """Akşam 19:00-22:00 Arası En İyi Sinyal"""
    try:
        logger.info("🌙 Akşam Sinyal Serisi hazırlanıyor...")
        if not SIGNAL_HISTORY:
            return
            
        # Son 24 saatteki en güvenilir BUY sinyalini bul
        recent_signals = [s for s in SIGNAL_HISTORY if s['type'] == 'BUY' and (datetime.now() - datetime.fromisoformat(s['timestamp'])).total_seconds() < 86400]
        
        if not recent_signals:
            safe_send_message(TELEGRAM_CHAT_ID, "🌙 Akşam Sinyali: Bugün için güçlü bir AL sinyali bulunamadı. Nakitte beklemek de bir pozisyondur. ☕")
            return
            
        best_signal = max(recent_signals, key=lambda x: x['confidence'])
        sym = best_signal['symbol']
        
        # Güncel veriyi çek
        bars = exchange.fetch_ohlcv(sym, '1h', limit=100)
        df = pd.DataFrame(bars, columns=['timestamp','open','high','low','close','volume'])
        df = calculate_indicators(df)
        last = df.iloc[-1]
        
        target = last['close'] * 1.06
        stop = last['close'] * 0.95
        
        msg = f"🚀 **AKŞAM SİNYALİ: {sym.split('/')[0]}** 🚀\n\n"
        msg += f"💰 Giriş: ${last['close']:.4f}\n"
        msg += f"🎯 Hedef: ${target:.4f}\n"
        msg += f"🛡️ Stop: ${stop:.4f}\n"
        msg += f"⭐ Güven Skoru: {best_signal['confidence']}/100\n\n"
        msg += f"Neden: {best_signal['reason']}\n\n"
        msg += f"👉 {TELEGRAM_CHANNEL_LINK}\n🔗 {LINKTREE_LINK}"
        
        chart_file = ChartGenerator.create_candlestick_chart(sym, df)
        if chart_file:
            with open(chart_file, 'rb') as photo:
                bot.send_photo(TELEGRAM_CHAT_ID, photo, caption=msg)
        else:
            safe_send_message(TELEGRAM_CHAT_ID, msg)
            
    except Exception as e:
        logger.error(f"Akşam serisi hatası: {e}")

def scheduled_twitter_analysis():
    """Top 4 coin için detaylı grafik ve AI destekli haftalık Twitter Thread (Haftaiçi 12:00, Haftasonu 20:00)"""
    if not GEMINI_API_KEY:
        logger.warning("Gemini API anahtarı yok, Thread üretimi atlanıyor.")
        return
        
    try:
        logger.info("🧵 [Twitter Analysis] Top 4 coin grafikleri ve AI Thread hazırlanıyor...")
        
        # İlk 4 coin'i al (USDT çiftleri ve update_symbols ile hacme göre sıralanmış)
        target_symbols = SYMBOLS[:4]
        
        photos = []
        chart_files = []
        analysis_data_list = []
        
        for symbol in target_symbols:
            logger.info(f"📊 {symbol} için veri çekiliyor ve grafik oluşturuluyor...")
            df = fetch_ohlcv_data(symbol, '1d', 100) # Günlük grafik
            if df is None or df.empty:
                continue
                
            df = calculate_indicators(df)
            
            # Grafik üret
            chart_file = ChartGenerator.create_candlestick_chart(symbol, df)
            if chart_file and os.path.exists(chart_file):
                chart_files.append(chart_file)
                photos.append(telebot.types.InputMediaPhoto(open(chart_file, 'rb')))
            
            # YZ Analizi için veriyi derle
            last_price = df['close'].iloc[-1]
            rsi = df['rsi'].iloc[-1]
            macd = df['macd'].iloc[-1]
            analysis_data_list.append(f"- {symbol}: Fiyat: {last_price:.4f}, RSI: {rsi:.1f}, MACD: {macd:.4f}")
            
        if not analysis_data_list:
            logger.warning("Analiz edilecek veri bulunamadı.")
            return

        # Gemini'ye prompt gönder
        prompt = f'''
        Sen efsanevi bir kripto analisti 'KriptoGraf'sın.
        Piyasanın en hacimli 4 kripto parası için güncel teknik analiz verilerini vereceğim. Grafikleri ben senin yerine ekleyeceğim, sen sadece yorumla.
        Bu veriler ışığında, bu 4 coin'i detaylıca değerlendiren çok kaliteli, heyecan verici ve profesyonel bir Twitter Flood'u (Thread) hazırla.
        
        Veriler:
        {chr(10).join(analysis_data_list)}
        
        Kurallar:
        1. İlk tweet kanca (hook) olsun, ilgi çekici başlasın.
        2. Toplam 4-5 tweetlik bir flood olsun. Her tweetin başında [1/5], [2/5] gibi numaratör olsun.
        3. Her bir coin için kısa, net ve vurucu teknik hedefler ile analiz ver.
        4. Samimi ama çok profesyonel ve ciddi bir Türkçe kullan. Emojileri dozunda kullan.
        5. Son tweet'e şunları ekle:
        "Beni Telegram'dan takip etmeyi unutmayın: TELEGRAM_LINK
        Tüm linklerim: LINKTREE_LINK" (bu kelimeleri aynen kullan)
        '''
        
        logger.info("🧠 [Twitter Analysis] Gemini AI'den yorum alınıyor...")
        response = client.models.generate_content(
            model=GEN_MODEL,
            contents=prompt
        )
        
        text = response.text.replace("TELEGRAM_LINK", TELEGRAM_CHANNEL_LINK).replace("LINKTREE_LINK", LINKTREE_LINK)
        
        logger.info("📤 Telegram'a Thread ve fotoğraflar gönderiliyor...")
        
        msg_text = f"🧵 **[GÜNLÜK TWITTER THREAD] Top 4 Coin Analizi:**\n\n{text}"
        
        if len(photos) > 0:
            # Albüm olarak gönder
            try:
                bot.send_media_group(TELEGRAM_CHAT_ID, photos)
                safe_send_message(TELEGRAM_CHAT_ID, msg_text)
            except Exception as e:
                logger.error(f"Media group gönderim hatası: {e}")
                # Hata olursa sadece text gönder
                safe_send_message(TELEGRAM_CHAT_ID, msg_text)
        else:
            safe_send_message(TELEGRAM_CHAT_ID, msg_text)
            
        # Temizlik
        for f in chart_files:
            try:
                os.remove(f)
            except:
                pass
                
        logger.info("✅ Twitter Analysis işlemi başarıyla tamamlandı!")
            
    except Exception as e:
        logger.error(f"scheduled_twitter_analysis hatası: {e}")


@bot.message_handler(commands=['thread'])
def generate_weekly_thread(message=None):
    """Haftalık AI Thread Üretimi"""
    if not GEMINI_API_KEY:
        if message: bot.reply_to(message, "❌ Gemini API anahtarı yok.")
        return
        
    try:
        if message: bot.reply_to(message, "🧵 Twitter/Telegram Thread'i AI ile hazırlanıyor. Lütfen bekleyin...")
        
        prompt = '''
        Sen efsanevi bir kripto analisti 'KriptoGraf'sın.
        2026 hedefli, 5x-10x potansiyelli altcoinler (özellikle GRT, AI, Web3, NVIDIA işbirlikleri odaklı) hakkında çok kaliteli bir Twitter Flood'u (Thread) hazırla.
        
        Kurallar:
        1. İlk tweet kanca (hook) olsun, ilgi çekici başlasın.
        2. Toplam 4-5 tweetlik bir flood olsun. Her tweetin başında [1/5], [2/5] gibi numaratör olsun.
        3. GRT (The Graph) için mutlaka en az 1 dolar hedefini temel analiziyle ver.
        4. Samimi ama çok profesyonel ve ciddi bir Türkçe kullan. Emojileri dozunda kullan.
        5. Son tweet'e şunları ekle:
        "Beni Telegram'dan takip etmeyi unutmayın: TELEGRAM_LINK
        Tüm linklerim: LINKTREE_LINK" (bu kelimeleri aynen kullan)
        '''
        
        response = client.models.generate_content(
            model=GEN_MODEL,
            contents=prompt
        )
        
        text = response.text.replace("TELEGRAM_LINK", TELEGRAM_CHANNEL_LINK).replace("LINKTREE_LINK", LINKTREE_LINK)
        
        # Telegram'a gönder
        if message:
            bot.send_message(message.chat.id, "🧵 **GÜNCEL THREAD HAZIR:**\n\n" + text)
        else:
            safe_send_message(TELEGRAM_CHAT_ID, "🧵 **YENİ HAFTALIK THREAD HAZIR:**\n\n" + text)
            
    except Exception as e:
        logger.error(f"Thread üretim hatası: {e}")

# ==========================================
# ANA DÖNGÜ
# ==========================================
def main_loop():
    """Ana döngü"""
    logger.info("🚀 ULTIMATE CRYPTO BOT - UPGRADED VERSION AKTİF!")
    
    # Database başlat
    Database.init_db()
    
    # İlk kurulum
    logger.info("📡 MEXC piyasalar taranıyor...")
    update_symbols()
    
    logger.info("📊 Korelasyon matrisi hesaplanıyor...")
    CorrelationAnalyzer.calculate_correlations()
    
    logger.info("🌐 Piyasa rejimi tespit ediliyor...")
    MarketRegimeDetector.detect_regime()
    
    logger.info(f"🧠 ML modelleri eğitiliyor ({len(SYMBOLS)} coin)...")
    for symbol in SYMBOLS[:10]: # Performans için ilk 10 coin'i eğit
        MLPredictor.train_model(symbol)
        time.sleep(2)
    
    # Zamanlanmış görevler (kademeli olarak çalışır, API yükü azaltılır)
    schedule.every(2).hours.do(update_symbols)                  # Dinamik coin güncellemeleri
    schedule.every(30).minutes.do(professional_signal_scanner)  # Teknik sinyal
    schedule.every(20).minutes.do(market_scanner)               # ML tarama
    schedule.every(60).minutes.do(CorrelationAnalyzer.calculate_correlations)  # Korelasyon
    schedule.every(30).minutes.do(MarketRegimeDetector.detect_regime)  # Rejim
    schedule.every().day.at("20:00").do(auto_hmap_report)         # Otomatik Heatmap
    schedule.every().day.at("20:45").do(auto_best_report)         # Otomatik En İyiler
    schedule.every().day.at("21:00").do(auto_worst_report)        # Otomatik En Kötüler
    schedule.every().day.at("21:15").do(daily_report)             # Günlük Genel Rapor (Saati kaydırdım)
    
    # VIP Rapor Saatleri
    # Hafta içi 12:30
    for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
        getattr(schedule.every(), day).at("12:30").do(scheduled_vip_report)
    
    # Hafta sonu 21:45
    for day in ['saturday', 'sunday']:
        getattr(schedule.every(), day).at("21:45").do(scheduled_vip_report)
    
    logger.info("✅ Tüm görevler zamanlandı!")
    logger.info("📡 Bot şimdi otomatik olarak:")
    logger.info("   • Piyasa Tarama: Her 2 Saatte")
    logger.info("   • Teknik Sinyal: 30 dakikada bir")
    logger.info("   • ML Radar: 20 dakikada bir")
    logger.info("   • Korelasyon: 60 dakikada bir")
    logger.info("   • Rejim Tespiti: 30 dakikada bir")
    logger.info("   • Günlük Rapor: 20:00'de")
    logger.info("   • Stop/Loss, Trailing, Take/Profit: sürekli")
    
    # İlk taramayı hemen yap
    logger.info("🚀 İlk taramalar başlatılıyor...")
    time.sleep(2)
    market_scanner()
    time.sleep(2)
    professional_signal_scanner()
    
    # GitHub Actions veya RUN_ONCE modundaysak tek turdan sonra çık
    if IS_CI_MODE:
        logger.info("🛑 GitHub Actions modunda tek tur tamamlandı. Durum kaydediliyor...")
        
        # ===== TWITTER ANALYSIS ZAMAN KONTROLÜ =====
        now_dt = datetime.now() # TRT saatine göre çalışıyor varsayarsak (sunucu saati TRT mi? UTC mi?)
        # GitHub Actions her zaman UTC kullanır! 
        # UTC 09:00 = TRT 12:00
        # UTC 17:00 = TRT 20:00
        now_utc = datetime.utcnow()
        weekday = now_utc.weekday() # 0=Pazartesi, 6=Pazar
        
        # GitHub Actions cron her 30m'de bir çalışıyor (XX:00 ve XX:30). Sadece ilk periyotta (XX:00 - XX:25) çalışmasını sağla ki çift mesaj atmasın.
        is_weekday_time = (weekday < 5) and (now_utc.hour == 9) and (now_utc.minute < 25)
        is_weekend_time = (weekday >= 5) and (now_utc.hour == 17) and (now_utc.minute < 25)
        
        if is_weekday_time or is_weekend_time:
            logger.info("⏰ Planlanan Twitter Analizi zamanı geldi. Başlatılıyor...")
            scheduled_twitter_analysis()
        else:
            logger.info(f"⏭️ Twitter Analizi atlandı (Zaman eşleşmedi). UTC: {now_utc.strftime('%H:%M')} Gün: {weekday}")
        # ============================================

        # Aktif pozisyon kontrollerini ve trader checklerini yap
        PortfolioTracker.check_active_positions()
        AutoTrader.check_active_trades()
        logger.info("👋 İşlem bitti, çıkılıyor.")
        return

    # Sonsuz döngü (Yerel çalışma için)
    while True:
        try:
            schedule.run_pending()
            PortfolioTracker.check_active_positions()  # Stop/Loss kontrolü
            AutoTrader.check_active_trades()           # Sanal Kaan botu işlemleri kontrolü
            time.sleep(30)
        except Exception as e:
            logger.error(f"Ana döngü hatası: {e}")
            time.sleep(60)

# ==========================================
# BAŞLAT
# ==========================================
# Arka planda botu başlatan ana fonksiyon (ASLA BLOKLAMAZ)
def run_bot_in_background():
    """Tüm servisleri ve bot döngüsünü arka planda başlatır"""
    try:
        if "bot_is_running" in st.session_state and st.session_state.bot_is_running:
            return
            
        logger.info("=" * 60)
        logger.info("🚀 ULTIMATE CRYPTO BOT - HUGGING FACE ASYNC START")
        logger.info("=" * 60)

        # 1. Database init
        Database.init_db()
        
        # 2. Ağır servisleri başlat (MEXC load markets vb.)
        init_all_services()
        
        # 3. Geçmiş sinyalleri yükle
        global SIGNAL_HISTORY
        try:
            SIGNAL_HISTORY = Database.get_recent_signals(limit=50)
            logger.info(f"📂 {len(SIGNAL_HISTORY)} geçmiş sinyal yüklendi.")
        except:
            SIGNAL_HISTORY = []
        
        # 4. Arka plan thread: main_loop (Döngüsel görevler)
        main_thread = threading.Thread(target=main_loop, daemon=True)
        main_thread.start()
        logger.info("✅ Arka plan görev döngüsü başlatıldı.")
        
        # 5. Telegram polling
        if bot:
            def start_polling():
                logger.info("📡 Telegram dinlemesi başlatılıyor...")
                try:
                    bot.infinity_polling(timeout=30, long_polling_timeout=30)
                except Exception as e:
                    logger.error(f"❌ Polling durdu: {e}")
            
            tg_thread = threading.Thread(target=start_polling, daemon=True)
            tg_thread.start()
            logger.info("✅ Telegram dinleme thread'i başlatıldı.")
        
        st.session_state.bot_is_running = True
        return True
    except Exception as e:
        logger.error(f"Arka plan başlatma hatası: {e}")
        return False

# Streamlit her saniye veya tetiklendiğinde burayı çalıştırır
if __name__ == "__main__":
    st.success("Hugging Face Sunucusu Başlatıldı! ✅")
    st.markdown("""
    ### Bot Durumu: **YÜKLENİYOR...** ⏳
    Bot servisleri (Borsa, Telegram, AI) şu an arka planda kuruluyor. 
    Bu işlem bittiğinde Telegram kanalınıza bildirim gelecektir.
    
    **Not:** Bu sayfa açık kalsa da kapansa da bot çalışmaya devam eder.
    """)
    
    # Botu bir kez başlat
    if "init_triggered" not in st.session_state:
        st.session_state.init_triggered = True
        threading.Thread(target=run_bot_in_background, daemon=True).start()
        st.info("Arka plan kurulumu tetiklendi. Bot 7/24 aktif olacaktır.")