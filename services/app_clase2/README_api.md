# Load Testing API

API construida con **FastAPI + Python 3.12** que expone tres endpoints para generar carga en CPU y RAM. Diseñada para correr en **Kubernetes sobre Google Cloud (GKE)**.

---

## Endpoints

| Método | Path | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Liveness check |
| `POST` | `/cpu` | Genera carga en CPU (proof-of-work con SHA-256) |
| `POST` | `/memory` | Genera y retiene usuarios aleatorios en RAM |
| `DELETE` | `/memory` | Limpia la lista en memoria (util para tests) |

Documentación interactiva disponible en `/docs` (Swagger UI).

---

## Uso de los endpoints

### GET /health
```bash
curl http://localhost:8000/health
```
```json
{"status": "ok", "users_in_memory": 0}
```

---

### POST /cpu
Busca un nonce tal que `SHA-256(data + nonce)` comience con el `prefix` indicado.  
**Cuanto más largo el prefijo, más iteraciones requiere** (carga exponencial).

```bash
curl -X POST http://localhost:8000/cpu \
  -H "Content-Type: application/json" \
  -d '{"data": "hola-mundo", "prefix": "00"}'
```
```json
{
  "hash": "00a3f1...",
  "nonce": 142,
  "iterations": 143,
  "prefix": "00"
}
```

> **Guía de carga:**
> | Prefijo | Iteraciones aprox. |
> |---------|-------------------|
> | `"0"` | ~16 |
> | `"00"` | ~256 |
> | `"000"` | ~4 096 |
> | `"0000"` | ~65 536 |
> | `"00000"` | ~1 000 000 |

---

### POST /memory
Genera `count` usuarios con `legajo` y `dni` aleatorios y los acumula en memoria.

```bash
curl -X POST http://localhost:8000/memory \
  -H "Content-Type: application/json" \
  -d '{"count": 100000}'
```
```json
{
  "added": 100000,
  "total_in_memory": 100000,
  "sample": [
    {"legajo": 483921, "dni": 37291048},
    ...
  ]
}
```

---

## Desarrollo local

### Con Docker Compose
```bash
# Construir y levantar
docker compose up --build

# Verificar
curl http://localhost:8000/health
```

### Sin Docker
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## Deploy en GKE

### 1. Construir y publicar la imagen
```bash
PROJECT_ID=tu-proyecto-gcp
IMAGE=gcr.io/$PROJECT_ID/load-api:latest

docker build -t $IMAGE .
docker push $IMAGE
```

### 2. Actualizar la imagen en el manifest
En `k8s-deployment.yaml`, reemplazar:
```yaml
image: load-api:latest
```
por:
```yaml
image: gcr.io/<PROJECT_ID>/load-api:latest
```

### 3. Aplicar el manifest
```bash
gcloud container clusters get-credentials <CLUSTER_NAME> --region <REGION>
kubectl apply -f k8s-deployment.yaml

# Verificar pods
kubectl get pods -n load-api

# Obtener IP externa del LoadBalancer
kubectl get svc -n load-api
```

---

## Estructura del proyecto

```
.
├── app/
│   └── main.py            # Aplicación FastAPI
├── Dockerfile             # Imagen multi-stage
├── docker-compose.yaml    # Entorno local
├── k8s-deployment.yaml    # Deployment + Service + HPA para GKE
├── requirements.txt       # Dependencias Python
└── README.md
```
