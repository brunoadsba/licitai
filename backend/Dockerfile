FROM python:3.12-slim

WORKDIR /app

# Dependências do sistema para parsing de documentos e Tesseract OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-por \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Criar diretório de uploads fora do web root
RUN mkdir -p /app/uploads && chmod 700 /app/uploads

EXPOSE 8000

# Rodar com uvicorn — bind em 0.0.0.0 DENTRO do container (acessível via Docker network)
# O docker-compose mapeia para 127.0.0.1 no host
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
