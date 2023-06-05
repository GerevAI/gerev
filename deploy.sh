#!/usr/bin/env bash
VERSION=0.0.4

cd ui || exit 1

npm install
npm run build

cd ..

mkdir -p $HOME/.gerev/.buildx-cache

docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 \
  --cache-from type=local,src=$HOME/.gerev/.buildx-cache \
  --cache-to type=local,dest=$HOME/.gerev/.buildx-cache \
  -t us-central1-docker.pkg.dev/gorgias-growth-production/growth-ops/gerev:$VERSION . \
  -t us-central1-docker.pkg.dev/gorgias-growth-production/growth-ops/gerev:latest --push
