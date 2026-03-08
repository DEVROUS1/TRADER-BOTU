FROM python:3.10-slim

WORKDIR /app

# Sistem bağımlılıklarını kur (matplotlib ve diğerleri için)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Dosyaları kopyala
COPY . .

# Python bağımlılıklarını kur
RUN pip3 install -r requirements.txt

# Streamlit portunu aç (Hugging Face 7860 bekler)
EXPOSE 7860

# Uygulamayı başlat
CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]
