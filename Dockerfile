# Build Stage 1 
# Build the UI
FROM node:12 AS node-builder

WORKDIR /app/ui

COPY ./ui/package.json .
RUN npm install --silent
RUN npm install react-scripts@3.0.1 -g

COPY ./ui .
RUN npm run build


# Build Stage 2
# Builds the backend as well as gets the built UI from Stage 1
FROM python:3.9
ENV CAPTURE_TELEMETRY=1
ENV DOCKER_DEPLOYMENT=1

WORKDIR /app

COPY ./app /app
RUN pip install -r /app/requirements.txt

# Cache the models
COPY ./app/models.py /tmp/models.py
RUN python3 /tmp/models.py

COPY --from=node-builder /app/ui/build ./ui
COPY ./run.sh /app/run.sh

VOLUME [ "/opt/storage" ]

EXPOSE 80
CMD ./run.sh
