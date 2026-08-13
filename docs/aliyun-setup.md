# Pomelo Aliyun Runtime Environment Setup Guide

## Overview

This guide covers creating all Aliyun cloud resources needed to run pomelo in production.

### Resources to create

| Resource | Count | Purpose |
|----------|-------|---------|
| RDS MySQL | 2 (test/prod) | Main database |
| Redis | 2 (test/prod) | Session store |
| OSS Bucket | 3 | Frontend static (×2) + video storage |
| NAS | 1 (shared) | Backend file storage (/kf/docs) |
| ACR namespace | 1 | Docker image registry (`ybbmb`) |
| DNS records | 2 | pomelo.dev.youbanban.com / pomelo.youbanban.com |

> ACK cluster is assumed to already exist (shared with kf). All resources in **cn-shanghai** region.

---

## 1. RDS MySQL (×2)

### 1.1 Create instances
1. Aliyun console → RDS → Create Instance
2. **Test**: MySQL 8.0, 2C4G (or smaller), cn-shanghai zone-A
3. **Prod**: MySQL 8.0, 4C8G, cn-shanghai zone-B
4. Set whitelist: add ACK cluster VPC CIDR + worker node security group

### 1.2 Configure accounts
- Create admin account (root / password) — save for `pomelo-db-root-secret`
- Create app account `pomelo` with password — used in `pomelo-secrets`

### 1.3 Connection info
Record for each instance:
- **DB_HOST**: RDS internal endpoint (e.g., `rm-xxx.mysql.cn-shanghai.rds.aliyuncs.com`)
- **DB_PORT**: `3306`
- **DB_NAME**: `pomelo` (created by init-db Job; RDS console has no db yet)
- **DB_USER**: `pomelo`
- **DB_PASSWORD**: `<app-password>`

---

## 2. Redis (×2)

### 2.1 Option A — Aliyun Tair/Redis
1. Console → Redis → Create Instance
2. **Test**: Community Edition 5.0, 1GB, cn-shanghai
3. **Prod**: Community Edition 5.0, 4GB, cn-shanghai (multi-zone)
4. Set password; whitelist cluster VPC CIDR

### 2.2 Option B — In-cluster Redis (StatefulSet)
If reusing an existing in-cluster Redis (e.g., `testredis1-master` in mb-test), skip A and use:
- **REDIS_HOST**: `testredis1-master.mb-test.svc.cluster.local` (test) / `testredis1-master.mb-pr.svc.cluster.local` (prod)
- **REDIS_PORT**: `6379`
- **REDIS_DB**: `0` (test) / `0` (prod)
- **REDIS_PASSWORD**: (from existing Redis)

> pomelo's `deploy/envs/test.env` already references `testredis1-master.mb-test.svc.cluster.local:6379` with password `Passw0rd`.

---

## 3. OSS Bucket (×3)

### 3.1 Frontend static buckets
1. Console → OSS → Create Bucket
2. **Test**: `pomelo-mb-test`, cn-shanghai, Standard, Public Read
3. **Prod**: `pomelo-mb-prod`, cn-shanghai, Standard, Public Read

### 3.2 Static website hosting (test/prod)
For each bucket:
1. Bucket → Basic Settings → Static Pages
2. Default page (索引页): `index.html`
3. 404 page (错误页): `200.html` — 必须是 `200.html`（Nuxt SPA 回退壳），否则客户端路由（如 `/admin/question-banks`）会返回 404 + 工作台页
4. Enable

### 3.3 Video bucket
1. **Video**: `pomelo-video`, cn-shanghai, Standard, Private (backend SDK access)

### 3.4 OSS static LB IP
OSS 静态网站 IP 按环境区分（见 `deploy/k8s/deploy.ps1`）：
- test: `47.102.237.237`
- prod: `106.14.228.188`

Verify:
```bash
nslookup pomelo-mb-test.oss-cn-shanghai.aliyuncs.com
```
If IP differs, update `deploy/k8s/oss-webui.yaml` Endpoints IP.

---

## 4. NAS File System

Pomelo shares the existing NAS with kf (same file system, same path `/kf/docs`).

- NAS server: `382934934e-qpp34.cn-shanghai.nas.aliyuncs.com`
- Path: `/kf/docs`
- PVC: `pomelo-storage` (100Gi, RWX, CSI `nasplugin.csi.alibabacloud.com`)

> No action needed if NAS already exists. Verify with:
> ```bash
> kubectl get pv pomelo-nas-pv
> ```

---

## 5. ACR (Container Registry)

1. Console → Container Registry → Namespace `ybbmb` (should already exist)
2. Create repository: `pomelo-backend`
3. Record ACR credentials (use RAM user or dedicated sub-account):
   - Registry: `registry.cn-shanghai.aliyuncs.com`
   - Namespace: `ybbmb`
   - Username: (from ACR console or RAM)
   - Password: (ACR password or RAM access key)

---

## 6. DNS (Domain)

### 6.1 Kong Ingress IP
Ingress 使用 Kong（`ingressClassName: kong-ext`，非 ALB）。获取 Kong 对外 LB 地址：
```bash
kubectl get ingress pomelo-ingress -n mb-test -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

### 6.2 DNS records
Add CNAME or A records at DNS provider:
- `pomelo.dev.youbanban.com` → (Kong LB IP)
- `pomelo.youbanban.com` → (Kong LB IP)

---

## 7. Secrets & Credentials

### 7.1 Required secret values
Fill `deploy/envs/test.env` and `deploy/envs/prod.env` with real values:

| Variable | Source | Example |
|----------|--------|---------|
| `DB_HOST` | RDS internal endpoint | `rm-xxx.mysql.cn-shanghai.rds.aliyuncs.com` |
| `DB_PORT` | RDS | `3306` |
| `DB_NAME` | RDS | `pomelo` |
| `DB_USER` | RDS app account | `pomelo` |
| `DB_PASSWORD` | RDS app password | (secure) |
| `REDIS_HOST` | Redis endpoint or in-cluster svc | `r-xxx.redis.cn-shanghai.rds.aliyuncs.com` |
| `REDIS_PORT` | Redis | `6379` |
| `REDIS_DB` | Redis | `0` |
| `REDIS_PASSWORD` | Redis password | (secure) |
| `JWT_SECRET` | Random 64 chars | `openssl rand -base64 48` |
| `DEEPSEEK_API_KEY` | DeepSeek API key | `sk-...` |
| `AI_STUDY_MAX_TOKENS` | 学习资料生成 token 上限 | `256000` |
| `AI_JSON_MODE` | DeepSeek JSON 输出模式 | `true` |
| `REGISTRATION_ENABLED` | 是否开放注册 | `false`（生产） |
| `CORS_ORIGINS` | Frontend domain | `https://pomelo.dev.youbanban.com` |
| `OSS_ACCESS_KEY_ID` | OSS RAM user AK | `LTAI5...` |
| `OSS_ACCESS_KEY_SECRET` | OSS RAM user SK | (secure) |
| `OSS_BUCKET` | Video bucket | `pomelo-video` |
| `OSS_ENDPOINT_INTERNAL` | OSS internal (k8s→oss) | `oss-cn-shanghai-internal.aliyuncs.com` |
| `OSS_ENDPOINT_PUBLIC` | OSS public (playback) | `oss-cn-shanghai.aliyuncs.com` |
| `OSS_VIDEO_PREFIX` | OSS video prefix | `videos/` |

> 完整配置键见 `backend/.env.example` 和 `deploy/k8s/secret.txt`。

### 7.2 Apply secrets
```bash
# From env file:
NAMESPACE=mb-test ENV_FILE=deploy/envs/test.env bash deploy/scripts/create-k8s-secrets.sh
NAMESPACE=mb-pr  ENV_FILE=deploy/envs/prod.env bash deploy/scripts/create-k8s-secrets.sh

# Or via deploy.ps1:
.\deploy\k8s\deploy.ps1 test -CreateSecret
```

---

## 8. Environment Setup Execution Order

### 8.1 Create cloud resources (manual, this guide §1-6)
- RDS ×2, Redis ×2, OSS ×3, NAS, ACR, DNS

### 8.2 One-time K8s setup (per namespace)
```powershell
.\deploy\scripts\create-env.ps1 test    # namespace + regsecret + pomelo-secrets + PV/PVC + OSS WebUI
.\deploy\scripts\create-env.ps1 prod
```

### 8.3 DB init (per namespace, one-time)
```bash
# 1. db-root-secret
kubectl -n mb-test create secret generic pomelo-db-root-secret \
  --from-literal=DB_ROOT_USER=root --from-literal=DB_ROOT_PASSWORD=<rds-root-pw>

# 2. Edit deploy/k8s/init-db-job.yaml: replace <RDS_HOST> and <NAMESPACE>
# 3. Apply
kubectl apply -f deploy/k8s/init-db-job.yaml

# 4. Verify job completed, then clean up
kubectl delete secret pomelo-db-root-secret -n mb-test
kubectl delete job init-pomelo-db -n mb-test
```

### 8.4 Deploy backend
```powershell
# Build + push image first
bash deploy/build-and-push.sh v1.0.0

# Deploy to K8s
.\deploy\k8s\deploy.ps1 test v1.0.0
.\deploy\k8s\deploy.ps1 prod v1.0.0
```

### 8.5 Run Alembic Migration
```bash
kubectl -n mb-test exec -it deployment/pomelo-backend -- alembic upgrade head
kubectl -n mb-pr  exec -it deployment/pomelo-backend -- alembic upgrade head
```

### 8.6 Deploy frontend
```powershell
.\deploy\oss-upload.ps1 test
.\deploy\oss-upload.ps1 prod
```

### 8.7 Verify
```bash
curl https://pomelo.dev.youbanban.com/health
curl https://pomelo.dev.youbanban.com/api/libraries
# Browse https://pomelo.dev.youbanban.com/
```

---

## 9. Troubleshooting

### OSS static site gives 403
- Check Kong host-header rewrite working: `curl -H "Host: pomelo-mb-test.oss-cn-shanghai.aliyuncs.com" https://pomelo.dev.youbanban.com/`
- If 403 persists, verify `oss-webui.yaml` Endpoints IP matches bucket IP (`nslookup`)
- Fallback: deploy nginx proxy pod → `deploy/k8s/oss-static-nginx.yaml` (not included, create if needed)

### Backend pod CrashLoopBackOff
- Check secrets: `kubectl describe pod -n mb-test <pod>`
- Check env vars: `kubectl exec deployment/pomelo-backend -n mb-test -- env | sort`
- Common: missing `DB_HOST`, `JWT_SECRET`, `DEEPSEEK_API_KEY` in pomelo-secrets

### Edge TTS fails
- Ensure egress from cluster to `speech.platform.bing.com:443` (NetworkPolicy / security group)
- Test: `kubectl exec deployment/pomelo-backend -n mb-test -- curl -s -o /dev/null -w '%{http_code}' https://speech.platform.bing.com`

### PV doesn't bind
- Check NAS CSI driver: `kubectl get csidrivers | grep nasplugin`
- Check PV: `kubectl describe pv pomelo-nas-pv`
- Verify NAS server/path correct in pv-nas.yaml
