# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Instalar dependencias en un entorno virtual aislado
COPY requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Usuario no-root para mayor seguridad en k8s
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Copiar el venv del builder
COPY --from=builder /opt/venv /opt/venv

# Copiar el código de la aplicación
COPY app/ ./app/

# Asignar permisos
RUN chown -R appuser:appgroup /app
USER appuser

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Uvicorn arranca la app; workers configurables por variable de entorno
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
