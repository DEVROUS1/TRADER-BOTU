FROM python:3.9-slim

WORKDIR /app

# Sistem bağımlılıklarını kur (matplotlib ve diğerleri için)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Dosyaları kopyala
COPY . .

# Python bağımlılıklarını kur
RUN pip3 install -r requirements.txt

# Streamlit portunu aç
EXPOSE 8501

# Uygulamayı başlat
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
