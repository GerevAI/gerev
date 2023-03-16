#!/usr/bin/env bash
VERSION=0.0.1

cd ui || exit 1

npm install
npm run build

cd ..

sudo docker buildx create --use
sudo docker buildx build --platform linux/amd64,linux/arm64 \
  -t gerev/gerev:$VERSION . \
  -t gerev/gerev:latest --push
