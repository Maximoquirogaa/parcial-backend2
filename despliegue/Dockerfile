FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Usuario sin privilegios; se crea antes del COPY para poder usar --chown.
RUN addgroup -S app && adduser -S app -G app

# Dependencias primero: la capa se reutiliza mientras requirements.txt no cambie.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app . .

USER app

EXPOSE 8000

# 127.0.0.1 explícito: en Alpine, localhost resuelve primero a ::1 (IPv6)
# y uvicorn con --host 0.0.0.0 escucha sólo IPv4.
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8000/health/ready || exit 1

# Si la base no responde, alembic falla y el contenedor termina con error.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
