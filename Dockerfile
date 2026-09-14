# Imagem do coletor de vagas.
FROM python:3.12-slim

# PYTHONDONTWRITEBYTECODE: não gera __pycache__ dentro do container.
# PYTHONUNBUFFERED: logs aparecem na hora no `docker compose logs`.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copia só o requirements primeiro: se o código mudar mas as dependências
# não, o Docker reaproveita a camada do pip install (build mais rápido).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY collector/ collector/

# O JSON é gravado em /app/docs/data/vagas.json (montado como volume no compose).
CMD ["python", "-m", "collector.main"]
