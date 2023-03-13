#!/bin/bash
# DO NOT run this file directly. use the docker.

/qdrant/qdrant --config-path /qdrant/config/config &

uvicorn main:app --host 0.0.0.0 --port 80 --env-file .env &

wait -n

exit $?
