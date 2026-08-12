#!/bin/bash
# ============================================================================
# pomelo-secrets management script — create / update from env
# ============================================================================
# Usage:
#   NAMESPACE=mb-test ./deploy/scripts/create-k8s-secrets.sh          # from env vars
#   NAMESPACE=mb-test ENV_FILE=deploy/envs/test.env ./deploy/scripts/create-k8s-secrets.sh
#   NAMESPACE=mb-test ./deploy/scripts/create-k8s-secrets.sh --show
# ============================================================================

set -euo pipefail

NAMESPACE="${NAMESPACE:-}"
ENV_FILE="${ENV_FILE:-${1:-}}"

if [[ "${1:-}" == "--show" ]]; then
    if [[ -z "$NAMESPACE" ]]; then
        echo "ERROR: NAMESPACE required (mb-test / mb-pr)"
        exit 1
    fi
    kubectl get secret pomelo-secrets -n "$NAMESPACE" -o yaml 2>/dev/null || echo "Secret not found"
    exit 0
fi

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: NAMESPACE=<ns> [ENV_FILE=<file>] ./deploy/scripts/create-k8s-secrets.sh [--show]"
    echo ""
    echo "  NAMESPACE     target K8s namespace (mb-test / mb-pr)"
    echo "  ENV_FILE      .env file path (optional; defaults to env vars)"
    echo "  --show        display current secret contents"
    echo "  -h, --help    show help"
    exit 0
fi

if [[ -n "$ENV_FILE" && -f "$ENV_FILE" ]]; then
    echo "Loading: $ENV_FILE"
    set -a
    source "$ENV_FILE"
    set +a
elif [[ -n "$ENV_FILE" ]]; then
    echo "ERROR: file not found: $ENV_FILE"
    exit 1
fi

if [[ -z "$NAMESPACE" ]]; then
    echo "ERROR: NAMESPACE required (mb-test / mb-pr)"
    exit 1
fi

# ---- defaults ----
OSS_ENDPOINT_INTERNAL="${OSS_ENDPOINT_INTERNAL:-oss-cn-shanghai-internal.aliyuncs.com}"
OSS_ENDPOINT_PUBLIC="${OSS_ENDPOINT_PUBLIC:-oss-cn-shanghai.aliyuncs.com}"
OSS_VIDEO_PREFIX="${OSS_VIDEO_PREFIX:-videos/}"
DB_POOL_SIZE="${DB_POOL_SIZE:-10}"
DB_MAX_OVERFLOW="${DB_MAX_OVERFLOW:-20}"
JWT_ALGORITHM="${JWT_ALGORITHM:-HS256}"
ACCESS_TOKEN_EXPIRE_MINUTES="${ACCESS_TOKEN_EXPIRE_MINUTES:-240}"
REFRESH_TOKEN_EXPIRE_DAYS="${REFRESH_TOKEN_EXPIRE_DAYS:-7}"
SESSION_TTL="${SESSION_TTL:-14400}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_DB="${REDIS_DB:-0}"
DEEPSEEK_BASE_URL="${DEEPSEEK_BASE_URL:-https://api.deepseek.com/v1}"
DEEPSEEK_MODEL="${DEEPSEEK_MODEL:-deepseek-v4-pro}"
DEEPSEEK_TIMEOUT="${DEEPSEEK_TIMEOUT:-900}"
DEEPSEEK_CONNECT_TIMEOUT="${DEEPSEEK_CONNECT_TIMEOUT:-5}"
AI_MAX_TOKENS="${AI_MAX_TOKENS:-16384}"
AI_QB_MAX_TOKENS="${AI_QB_MAX_TOKENS:-256000}"
AI_DOC_MAX_CHARS="${AI_DOC_MAX_CHARS:-5000}"
AI_TOTAL_MAX_CHARS="${AI_TOTAL_MAX_CHARS:-40000}"
AI_TEMPERATURE="${AI_TEMPERATURE:-0.7}"
APP_PORT="${APP_PORT:-8080}"
APP_ENV="${APP_ENV:-production}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"
LOG_FORMAT="${LOG_FORMAT:-json}"
DOCS_ROOT="${DOCS_ROOT:-/app/data/storage}"
PROMPTS_FILE="${PROMPTS_FILE:-config/prompts.yaml}"
TTS_DEFAULT_VOICE="${TTS_DEFAULT_VOICE:-zh-CN-XiaoxiaoNeural}"
TTS_AVAILABLE_VOICES="${TTS_AVAILABLE_VOICES:-zh-CN-XiaoxiaoNeural,zh-CN-YunxiNeural,zh-CN-YunjianNeural,zh-CN-XiaoyiNeural,zh-CN-YunyangNeural}"
TTS_FALLBACK_CHARS_PER_SEC="${TTS_FALLBACK_CHARS_PER_SEC:-4.5}"
DB_PORT="${DB_PORT:-3306}"

echo "Creating / updating pomelo-secrets (namespace=$NAMESPACE) ..."

kubectl create secret generic pomelo-secrets \
    --namespace="$NAMESPACE" \
    --dry-run=client -o yaml \
    --from-literal=DB_HOST="${DB_HOST:-}" \
    --from-literal=DB_PORT="$DB_PORT" \
    --from-literal=DB_NAME="${DB_NAME:-pomelo}" \
    --from-literal=DB_USER="${DB_USER:-pomelo}" \
    --from-literal=DB_PASSWORD="${DB_PASSWORD:-}" \
    --from-literal=DB_POOL_SIZE="$DB_POOL_SIZE" \
    --from-literal=DB_MAX_OVERFLOW="$DB_MAX_OVERFLOW" \
    --from-literal=REDIS_HOST="${REDIS_HOST:-}" \
    --from-literal=REDIS_PORT="$REDIS_PORT" \
    --from-literal=REDIS_DB="$REDIS_DB" \
    --from-literal=REDIS_PASSWORD="${REDIS_PASSWORD:-}" \
    --from-literal=JWT_SECRET="${JWT_SECRET:-}" \
    --from-literal=JWT_ALGORITHM="$JWT_ALGORITHM" \
    --from-literal=ACCESS_TOKEN_EXPIRE_MINUTES="$ACCESS_TOKEN_EXPIRE_MINUTES" \
    --from-literal=REFRESH_TOKEN_EXPIRE_DAYS="$REFRESH_TOKEN_EXPIRE_DAYS" \
    --from-literal=SESSION_TTL="$SESSION_TTL" \
    --from-literal=DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-}" \
    --from-literal=DEEPSEEK_BASE_URL="$DEEPSEEK_BASE_URL" \
    --from-literal=DEEPSEEK_MODEL="$DEEPSEEK_MODEL" \
    --from-literal=DEEPSEEK_TIMEOUT="$DEEPSEEK_TIMEOUT" \
    --from-literal=DEEPSEEK_CONNECT_TIMEOUT="$DEEPSEEK_CONNECT_TIMEOUT" \
    --from-literal=AI_MAX_TOKENS="$AI_MAX_TOKENS" \
    --from-literal=AI_QB_MAX_TOKENS="$AI_QB_MAX_TOKENS" \
    --from-literal=AI_DOC_MAX_CHARS="$AI_DOC_MAX_CHARS" \
    --from-literal=AI_TOTAL_MAX_CHARS="$AI_TOTAL_MAX_CHARS" \
    --from-literal=AI_TEMPERATURE="$AI_TEMPERATURE" \
    --from-literal=CORS_ORIGINS="${CORS_ORIGINS:-}" \
    --from-literal=APP_ENV="$APP_ENV" \
    --from-literal=APP_PORT="$APP_PORT" \
    --from-literal=LOG_LEVEL="$LOG_LEVEL" \
    --from-literal=LOG_FORMAT="$LOG_FORMAT" \
    --from-literal=DOCS_ROOT="$DOCS_ROOT" \
    --from-literal=PROMPTS_FILE="$PROMPTS_FILE" \
    --from-literal=TTS_DEFAULT_VOICE="$TTS_DEFAULT_VOICE" \
    --from-literal=TTS_AVAILABLE_VOICES="$TTS_AVAILABLE_VOICES" \
    --from-literal=TTS_FALLBACK_CHARS_PER_SEC="$TTS_FALLBACK_CHARS_PER_SEC" \
    --from-literal=OSS_ACCESS_KEY_ID="${OSS_ACCESS_KEY_ID:-}" \
    --from-literal=OSS_ACCESS_KEY_SECRET="${OSS_ACCESS_KEY_SECRET:-}" \
    --from-literal=OSS_BUCKET="${OSS_BUCKET:-}" \
    --from-literal=OSS_ENDPOINT_INTERNAL="$OSS_ENDPOINT_INTERNAL" \
    --from-literal=OSS_ENDPOINT_PUBLIC="$OSS_ENDPOINT_PUBLIC" \
    --from-literal=OSS_VIDEO_PREFIX="$OSS_VIDEO_PREFIX" \
| kubectl apply -f -

echo "Done: pomelo-secrets updated (namespace=$NAMESPACE)"

kubectl get secret pomelo-secrets -n "$NAMESPACE" -o 'go-template={{range $k,$v := .data}}{{$k}}: {{printf "%.5s... (%d chars)\n" $v (len $v)}}{{end}}' 2>/dev/null || echo "(Verify with: kubectl get secret pomelo-secrets -n $NAMESPACE)"
