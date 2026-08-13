# Pomelo K8s Deployment

## Environment Reference

| | Test | Prod |
|---|------|------|
| Namespace | `mb-test` | `mb-pr` |
| Domain | `pomelo.dev.youbanban.com` | `pomelo.youbanban.com` |
| OSS Bucket | `pomelo-mb-test` | `pomelo-mb-prod` |
| ACR Image | `registry.cn-shanghai.aliyuncs.com/ybbmb/pomelo-backend:<TAG>` | same |

## Prerequisites

- `kubectl` configured to ACK cluster
- `ossutil` configured (or `/mnt/ossutil` on Jenkins agent)
- Docker with ACR login (`docker login registry.cn-shanghai.aliyuncs.com`)
- Node.js + pnpm (for frontend build; pre-committed dist uploaded via pipeline)

## One-Time Env Setup (per namespace, mb-test / mb-pr)

```powershell
# Automated (recommended):
.\deploy\scripts\create-env.ps1 test    # Creates: namespace, regsecret, pomelo-secrets, PV/PVC, OSS WebUI
.\deploy\scripts\create-env.ps1 prod

# Manual steps if needed:
# 1. Namespace: kubectl apply -f deploy/k8s/namespace.yaml (with <NAMESPACE> replaced)
# 2. ACR pull secret:
#    kubectl -n mb-test create secret docker-registry regsecret \
#      --docker-server=registry.cn-shanghai.aliyuncs.com \
#      --docker-username=<ACR_USER> --docker-password=<ACR_PASSWORD>
# 3. pomelo-secrets: see deploy/k8s/secret.txt; fill values and apply
# 4. PV + PVC: kubectl apply -f deploy/k8s/pv-nas.yaml (with <NAMESPACE> replaced)
# 5. OSS WebUI: kubectl apply -f deploy/k8s/oss-webui.yaml (with <NAMESPACE> replaced)
```

## OSS Static Website Config (one-time, per bucket)

The frontend is a Nuxt SPA. Deep links (e.g. `/admin/question-banks`) only work if the OSS
bucket's **error page (默认 404 页)** points to `200.html` (the SPA fallback shell) — NOT
`index.html`. Set this in the OSS console, or via the Aliyun SDK:

```python
# Set OSS website config: index page = index.html, error page = 200.html
import oss2
from oss2.models import BucketWebsite
b = oss2.Bucket(oss2.Auth('<AK>', '<SK>'), 'https://oss-cn-shanghai.aliyuncs.com', '<BUCKET>')
b.put_bucket_website(BucketWebsite(index_file='index.html', error_file='200.html'))
```

- `index_file = index.html`  → `/` serves the workbench.
- `error_file = 200.html`  → any unknown path serves the SPA shell (client-side routing).
- Note: OSS serves the error page with HTTP 404 status even though the page renders correctly.

## DB Initialization (first deploy only)

```bash
# 1. Create root secret (one-time, remove after job completes)
kubectl -n mb-test create secret generic pomelo-db-root-secret \
  --from-literal=DB_ROOT_USER=root \
  --from-literal=DB_ROOT_PASSWORD=<RDS-root-password>

# 2. Edit deploy/k8s/init-db-job.yaml: replace <RDS_HOST> and <NAMESPACE> with actual values
# 3. Run init-db job (creates pomelo database + app user)
kubectl apply -f deploy/k8s/init-db-job.yaml

# 4. After job completes (kubectl get job init-pomelo-db -n mb-test)
kubectl delete secret pomelo-db-root-secret -n mb-test   # remove root creds
kubectl delete job init-pomelo-db -n mb-test              # clean up job (auto TTL 300s)

# 5. Run Alembic migration
kubectl -n mb-test exec -it deployment/pomelo-backend -- alembic upgrade head
```

## Deploy

### Backend (Build & Push + K8s)
```powershell
# In WSL or CI pipeline:
bash deploy/build-and-push.sh v1.0.0         # build + push
# Then deploy:
.\deploy\k8s\deploy.ps1 test v1.0.0          # K8s apply
```

### Frontend (Build & Upload OSS)
```powershell
.\deploy\oss-upload.ps1 test       # pomelo-mb-test
.\deploy\oss-upload.ps1 prod       # pomelo-mb-prod
```

## Verify

```bash
kubectl get pods -n mb-test -w
kubectl logs -n mb-test deployment/pomelo-backend

curl https://pomelo.dev.youbanban.com/health       # → {"status":"healthy"}
curl https://pomelo.dev.youbanban.com/api/libraries
```

## K8s Resources

| Resource | Name |
|----------|------|
| Namespace | `mb-test` / `mb-pr` |
| Deployment | `pomelo-backend` |
| Service | `pomelo-backend:8080` |
| PVC | `pomelo-storage` (NAS, /kf/docs) |
| Ingress | `pomelo-ingress` (Kong, `kong-ext`) |
| Secret | `pomelo-secrets` |
| Secret | `regsecret` (ACR pull) |
| OSS Service | `pomelo-oss-webui` (ClusterIP + Endpoints → OSS IP) |

## Egress Requirements

> Edge TTS requires outbound access to `speech.platform.bing.com:443`. Ensure NetworkPolicy/security group allows this or TTS will silently fail.
