import os
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ HATA: GEMINI_API_KEY bulunamadı!")
    exit(1)

try:
    client = genai.Client(api_key=GEMINI_API_KEY)
    print("📋 Mevcut Modeller:")
    for m in client.models.list():
        print(f"- {m.name}")
except Exception as e:
    print(f"❌ HATA: Modeller listelenemedi: {e}")
