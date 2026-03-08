import os
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ HATA: GEMINI_API_KEY bulunamadı!")
    exit(1)

try:
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    print("🔄 Gemini Pro Latest ile test ediliyor...")
    response = client.models.generate_content(
        model='gemini-pro-latest',
        contents="Merhaba!"
    )
    
    print(f"✅ Gemini Yanıtı: {response.text.strip()}")
    print("🚀 API Anahtarı çalışıyor!")
except Exception as e:
    print(f"❌ HATA: Test başarısız: {e}")
