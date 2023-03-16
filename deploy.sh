#!/bin/bash
VERSION=0.0.1

cd ui

npm install
npm run build

cd ..

sudo docker build -t gerev/gerev:$VERSION .
sudo docker tag gerev/gerev:$VERSION gerev/gerev:latest

sudo docker push gerev/gerev:$VERSION
sudo docker push gerev/gerev:latest

