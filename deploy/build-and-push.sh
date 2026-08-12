#!/bin/bash
# Pomelo Backend: Build Docker Image & Push to ACR
# Run this INSIDE WSL
#
# Usage:
#   bash deploy/build-and-push.sh             # build with git short hash
#   bash deploy/build-and-push.sh v1.0.0       # build with custom tag
#   bash deploy/build-and-push.sh v1.0.0 -l    # also push :latest

set -euo pipefail

TAG="${1:-$(git -C /mnt/d/workspace/pomelo rev-parse --short HEAD)}"
PUSH_LATEST=false
if [ "${2:-}" = "-l" ]; then PUSH_LATEST=true; fi

ACR_NS="ybbmb"           # TODO: replace with your ACR namespace
ACR_EXTERNAL="registry.cn-shanghai.aliyuncs.com"
ACR_INTERNAL="registry-vpc.cn-shanghai.aliyuncs.com"
IMAGE="pomelo-backend"

cd /mnt/d/workspace/pomelo/backend

echo "Building $IMAGE:$TAG ..."
docker build -t "${IMAGE}:${TAG}" .

EXT_TAG="${ACR_EXTERNAL}/${ACR_NS}/${IMAGE}:${TAG}"
INT_TAG="${ACR_INTERNAL}/${ACR_NS}/${IMAGE}:${TAG}"

docker tag "${IMAGE}:${TAG}" "$EXT_TAG"
docker push "$EXT_TAG"
echo "Pushed $EXT_TAG"

docker tag "${IMAGE}:${TAG}" "$INT_TAG"
docker push "$INT_TAG"
echo "Pushed $INT_TAG"

if $PUSH_LATEST; then
    docker tag "${IMAGE}:${TAG}" "${ACR_EXTERNAL}/${ACR_NS}/${IMAGE}:latest"
    docker push "${ACR_EXTERNAL}/${ACR_NS}/${IMAGE}:latest"
    echo "Pushed latest"
fi

echo "Done."
