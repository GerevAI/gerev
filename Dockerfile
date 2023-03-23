# Stage 1: Build the React Native app
FROM node:lts-alpine as build-stage

WORKDIR /ui

# Copy the package.json and package-lock.json files
COPY ./ui/package*.json ./

# Install dependencies
RUN npm ci

# Copy the rest of the app
COPY ./ui .

# Build the app
RUN npm run build

# Stage 2: Set up Python environment
FROM python:3.9

# Install torch
RUN pip install torch

# Install Python requirements
COPY ./app/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# Set telemetry environment variable
ENV CAPTURE_TELEMETRY=1

# Cache the models
COPY ./app/models.py /tmp/models.py
RUN python3 /tmp/models.py

# Copy the Python app
COPY ./app /app

# Copy the built React Native app from the build stage
COPY --from=build-stage /ui/build /ui

# Copy run script
COPY ./run.sh /app/run.sh

# Set the working directory
WORKDIR /app

# Create volume for storage
VOLUME [ "/opt/storage" ]

EXPOSE 80

CMD ./run.sh
