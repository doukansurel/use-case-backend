# ==============================================================================
# VisionQC Backend - Production-Ready Dockerfile
# Python 3.12 Slim tabanlı, güvenli ve optimize edilmiş konteyner imajı
# ==============================================================================
FROM python:3.12-slim AS runner

# Ortam değişkenleri: Python çıktı tamponlamasını kapat, bytecode üretimini engelle
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000 \
    HOST=0.0.0.0

# Çalışma dizini
WORKDIR /app

# Sağlık kontrolü (healthcheck) ve temel ağ sertifikaları için curl ve ca-certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Güvenlik: Uygulama için unprivileged (ayrıcalıksız) kullanıcı ve grup oluştur
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup --no-create-home appuser

# Bağımlılıkları kopyala ve yükle (Docker cache katmanlaması için önce requirements)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kaynak kodlarını kopyala
COPY app/ ./app
COPY run.py .

# Çalışma dizinindeki dosyaların sahipliğini appuser'a devret
RUN chown -R appuser:appgroup /app

# Ayrıcalıksız kullanıcıya geçiş yap
USER appuser

# Port tanımlaması
EXPOSE 8000

# Konteyner Sağlık Kontrolü (Healthcheck)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Uygulama başlatma komutu
CMD ["python", "run.py", "--host", "0.0.0.0", "--port", "8000"]
