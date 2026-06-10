import hashlib
import random
from typing import List
from contextlib import asynccontextmanager
from concurrent.futures import ProcessPoolExecutor

import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import gc
import ctypes



# ─── Executor lifecycle ───────────────────────────────────────────────────────
# ProcessPoolExecutor: cada worker corre en su propio proceso → bypasses GIL.
# Se inicializa en lifespan para que exista exactamente una instancia por
# proceso de uvicorn y se destruya limpiamente al shutdown.

executor: ProcessPoolExecutor | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global executor
    # Limitar workers al CPU disponible en el container
    # 360m ≈ 0.36 CPU → 1 worker es lo correcto para este límite
    executor = ProcessPoolExecutor(max_workers=1)
    yield
    executor.shutdown(wait=False)


app = FastAPI(
    title="Load Testing API",
    description="API para generación de carga en CPU y memoria RAM",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── Estado en memoria ────────────────────────────────────────────────────────
users_in_memory: List[dict] = []


# ─── Schemas ─────────────────────────────────────────────────────────────────
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


# ─── Funciones de trabajo ─────────────────────────────────────────────────────
# Deben ser pickleable (definidas a nivel de módulo) para ProcessPoolExecutor.
# NO lanzan HTTPException: las excepciones entre procesos se serializan como
# tipos estándar; FastAPI no puede catchear HTTPException fuera de su contexto.

def _compute_hash(data: str, prefix: str) -> dict:
    nonce = 0
    while True:
        digest = hashlib.sha256(f"{data}{nonce}".encode()).hexdigest()
        if digest.startswith(prefix):
            return {
                "hash": digest,
                "nonce": nonce,
                "iterations": nonce + 1,
                "prefix": prefix,
            }
        nonce += 1
        if nonce > 10_000_000:
            # ValueError viaja correctamente entre procesos via pickle
            raise ValueError("Prefijo no encontrado en 10 000 000 iteraciones")


def _generate_users(count: int) -> list:
    return [
        {
            "legajo": random.randint(10_000, 999_999),
            "dni": random.randint(1_000_000, 99_999_999),
        }
        for _ in range(count)
    ]


# ─── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    return HealthResponse(status="ok", users_in_memory=len(users_in_memory))


@app.post("/cpu", response_model=CPUResponse, tags=["CPU"])
async def cpu_load(request: CPURequest):
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(
            executor, _compute_hash, request.data, request.prefix
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return result


@app.post("/memory", response_model=MemoryResponse, tags=["Memory"])
async def memory_load(request: MemoryRequest):
    # asyncio.to_thread usa el ThreadPoolExecutor default del loop.
    # Apropiado acá: la generación es mayormente memoria/random, no cómputo puro.
    new_users = await asyncio.to_thread(_generate_users, request.count)
    users_in_memory.extend(new_users)
    return MemoryResponse(
        added=len(new_users),
        total_in_memory=len(users_in_memory),
        sample=new_users[:5],
    )

def _release_memory() -> None:
    gc.collect()
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)  # devuelve páginas libres al OS (Linux)
    except Exception:
        pass

@app.delete("/memory", tags=["Memory"])
async def clear_memory():
    count = len(users_in_memory)
    users_in_memory.clear()
    await asyncio.to_thread(_release_memory)
    return {"cleared": count, "total_in_memory": 0}
