# Python 3.9 tabanlı bir imaj kullan
FROM python:3.9-slim

# Sistem paketlerini güncelle ve ffmpeg'i yükle
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Çalışma dizinini oluştur
WORKDIR /app

# Gereken dosyaları kopyala
COPY requirements.txt /app/
COPY esek.py /app/
COPY main.py /app/

# Bağımlılıkları yükle
RUN pip install --no-cache-dir -r requirements.txt

# Uygulamanızı başlat
CMD ["python3", "main.py"]