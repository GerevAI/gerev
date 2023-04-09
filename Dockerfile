# Build Stage 1 
# Build the UI
FROM node:12 AS node-builder

WORKDIR /app/ui

COPY ./ui/package.json .
RUN npm install --silent --production

COPY ./ui .
RUN npm run build


# Build Stage 2
# Builds the backend as well as gets the built UI from Stage 1
FROM python:3.9
ENV CAPTURE_TELEMETRY=1

WORKDIR /app

COPY ./app/requirements.txt .
RUN pip install -r /app/requirements.txt

COPY ./app /app

# Cache the models
COPY ./app/models.py /tmp/models.py
RUN python3 /tmp/models.py

COPY --from=node-builder /app/ui/build /ui
COPY ./run.sh .

ENV DOCKER_DEPLOYMENT=1

EXPOSE 80
CMD ./run.sh
