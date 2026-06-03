# k8s-exercise

FastAPI + NiceGUI desplegados en Google Kubernetes Engine, provisionado con Terraform.

---

## Arquitectura

```
Internet
    │
    ▼
GCP HTTP Load Balancer (IP externa)
    │
    ▼
Ingress (GCE)
    │  path: /
    ▼
frontend-service (ClusterIP :8080)
    │  USERS_API_URL=http://users-api-service:8000
    ▼
users-api-service (ClusterIP :8000)  ← sin acceso externo
```

- `services/users-api` — FastAPI, CRUD de usuarios en memoria, puerto 8000
- `services/frontend` — NiceGUI, consume la API, puerto 8080
- `terraform/` — VPC, GKE cluster, Artifact Registry
- `k8s/` — Deployments, Services, Ingress

---

## Prerequisitos

- gcloud CLI
- terraform
- kubectl + gke-gcloud-auth-plugin
- docker
- Cuenta GCP con billing activo

---

## Deploy

### 1. Proyecto GCP

```bash
gcloud auth login
gcloud projects create <PROJECT_ID>
gcloud config set project <PROJECT_ID>
gcloud billing projects link <PROJECT_ID> --billing-account=<BILLING_ACCOUNT_ID>
```

Para obtener el `BILLING_ACCOUNT_ID`: `gcloud billing accounts list`

### 2. Infraestructura

```bash
gcloud auth application-default login
cd terraform
terraform init
terraform apply -var="project_id=<PROJECT_ID>"
```

Tarda ~10 minutos. Al finalizar imprime la URL del Artifact Registry y el comando para configurar kubectl.

### 3. Imágenes Docker

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev

docker build -t us-central1-docker.pkg.dev/<PROJECT_ID>/k8s-exercise/users-api:latest services/users-api/
docker push us-central1-docker.pkg.dev/<PROJECT_ID>/k8s-exercise/users-api:latest

docker build -t us-central1-docker.pkg.dev/<PROJECT_ID>/k8s-exercise/frontend:latest services/frontend/
docker push us-central1-docker.pkg.dev/<PROJECT_ID>/k8s-exercise/frontend:latest
```

### 4. kubectl

Instalar el plugin de autenticación:

```bash
# Arch Linux
yay -S google-cloud-cli-gke-gcloud-auth-plugin

# Debian/Ubuntu
sudo apt-get install google-cloud-cli-gke-gcloud-auth-plugin
```

Configurar el contexto (el comando exacto lo da `terraform output kubeconfig_command`):

```bash
gcloud container clusters get-credentials <PROJECT_ID>-gke \
  --region us-central1 --project <PROJECT_ID>
```

### 5. Manifiestos

```bash
kubectl apply -f k8s/users-api/
kubectl apply -f k8s/frontend/
kubectl apply -f k8s/ingress.yaml
```

Esperar la IP externa del Ingress (3-5 minutos):

```bash
kubectl get ingress main-ingress --watch
```

La UI queda accesible en `http://<EXTERNAL_IP>`.

---

## Cleanup

### 1. Eliminar recursos Kubernetes con exposición externa

Eliminar primero el Ingress para que GKE destruya el Load Balancer, Backend Services y Network Endpoint Groups (NEGs) asociados:

```bash
kubectl delete -f k8s/ingress.yaml
```

Verificar que los recursos gestionados por GKE desaparezcan:

```bash
gcloud compute network-endpoint-groups list
gcloud compute backend-services list
gcloud compute forwarding-rules list
```

Esperar hasta que no existan recursos con prefijo `k8s1-`.

### 2. Eliminar aplicaciones

```bash
kubectl delete -f k8s/frontend/
kubectl delete -f k8s/users-api/
```

### 3. Destruir infraestructura

```bash
cd terraform
terraform destroy -var="project_id=<PROJECT_ID>"
```

### Verificación opcional

Si `terraform destroy` falla indicando que la VPC sigue en uso, comprobar recursos huérfanos:

```bash
gcloud compute network-endpoint-groups list
gcloud compute backend-services list
gcloud compute forwarding-rules list
gcloud compute addresses list
```

Los recursos `k8s1-*` suelen indicar que la limpieza del Ingress aún no finalizó.

---

## Problema conocido: Quota SSD_TOTAL_GB excedida

### Síntoma

```
Error: Quota 'SSD_TOTAL_GB' exceeded. Limit: 250.0 in region us-central1.
```

### Causa

GKE crea un nodo inicial obligatorio para bootstrappear el cluster antes de levantar el node pool definitivo. Sin `node_config` explícito en el recurso `google_container_cluster`, ese nodo usa disco `pd-balanced` (SSD, 100GB) por defecto.

En cuentas nuevas la quota de SSD suele ser 250GB. Si `terraform apply` falla y se reintenta sin hacer `terraform destroy` primero, cada intento deja un disco SSD huérfano acumulando quota.

### Diagnóstico

```bash
# Ver quota actual
gcloud compute regions describe us-central1 --project=<PROJECT_ID> \
  --format="table(quotas.metric,quotas.limit,quotas.usage)" | grep SSD

# Ver discos huérfanos
gcloud compute disks list --project=<PROJECT_ID>
```

### Solución

El `terraform/main.tf` ya incluye `node_config` con `disk_type = "pd-standard"` en el cluster resource para evitar este problema. Si aun así ocurre por discos de intentos anteriores, borrarlos manualmente y verificar que la quota vuelve a 0 antes de reintentar:

```bash
gcloud compute disks delete <DISK_NAME> --zone=<ZONE> --project=<PROJECT_ID> --quiet
terraform destroy -var="project_id=<PROJECT_ID>"
terraform apply -var="project_id=<PROJECT_ID>"
```
