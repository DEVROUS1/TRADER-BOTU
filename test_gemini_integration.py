import os
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ HATA: GEMINI_API_KEY bulunamadı!")
    exit(1)

try:
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    print("🔄 Gemini 3.1 Pro (Preview) test ediliyor...")
    response = client.models.generate_content(
        model='gemini-3.1-pro-preview',
        contents="Merhaba, sen bir kripto trading asistanısın. Kısa bir selam ver."
    )
    
    print(f"✅ Gemini Yanıtı: {response.text.strip()}")
    print("🚀 Entegrasyon başarılı!")
except Exception as e:
    print(f"❌ HATA: Gemini testi başarısız: {e}")
