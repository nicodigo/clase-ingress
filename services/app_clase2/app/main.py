import hashlib
import random
import string
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="Load Testing API",
    description="API para generación de carga en CPU y memoria RAM",
    version="1.0.0",
)

# ─── Estado en memoria ────────────────────────────────────────────────────────

users_in_memory: List[dict] = []


# ─── Schemas ──────────────────────────────────────────────────────────────────

class CPURequest(BaseModel):
    data: str = Field(..., description="String de entrada para hashear")
    prefix: str = Field(..., description="Prefijo que debe tener el hash resultante")


class CPUResponse(BaseModel):
    hash: str
    nonce: int
    iterations: int
    prefix: str


class MemoryRequest(BaseModel):
    count: int = Field(..., gt=0, description="Cantidad de usuarios a generar y retener en memoria")


class MemoryResponse(BaseModel):
    added: int
    total_in_memory: int
    sample: List[dict]


class HealthResponse(BaseModel):
    status: str
    users_in_memory: int


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Verifica que la API esté operativa."""
    return HealthResponse(
        status="ok",
        users_in_memory=len(users_in_memory),
    )


@app.post("/cpu", response_model=CPUResponse, tags=["CPU"])
def cpu_load(request: CPURequest):
    """
    Genera carga en CPU buscando un nonce tal que:
    SHA-256(data + nonce) empiece con el prefijo indicado.

    Equivalente a un mini proof-of-work.
    """
    prefix = request.prefix.lower()
    base = request.data
    nonce = 0

    while True:
        candidate = f"{base}{nonce}".encode()
        digest = hashlib.sha256(candidate).hexdigest()
        if digest.startswith(prefix):
            return CPUResponse(
                hash=digest,
                nonce=nonce,
                iterations=nonce + 1,
                prefix=prefix,
            )
        nonce += 1

        # Límite de seguridad para evitar loops infinitos ante prefijos imposibles
        if nonce > 10_000_000:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"No se encontró hash con prefijo '{prefix}' "
                    f"en 10.000.000 iteraciones. Usá un prefijo más corto."
                ),
            )


@app.post("/memory", response_model=MemoryResponse, tags=["Memory"])
def memory_load(request: MemoryRequest):
    """
    Genera `count` usuarios con legajo y DNI aleatorios y los retiene en memoria RAM.
    Los datos se acumulan en cada llamada (no se reinicia la lista).
    """
    new_users = [
        {
            "legajo": random.randint(10_000, 999_999),
            "dni": random.randint(1_000_000, 99_999_999),
        }
        for _ in range(request.count)
    ]
    users_in_memory.extend(new_users)

    # Muestra de hasta 5 usuarios recién agregados en la respuesta
    sample = new_users[:5]

    return MemoryResponse(
        added=len(new_users),
        total_in_memory=len(users_in_memory),
        sample=sample,
    )


@app.delete("/memory", tags=["Memory"])
def clear_memory():
    """Limpia la lista de usuarios en memoria (útil para tests)."""
    count = len(users_in_memory)
    users_in_memory.clear()
    return {"cleared": count, "total_in_memory": 0}
