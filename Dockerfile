FROM python:3.9

RUN pip install torch

COPY ./app/requirements.txt /tmp/requirements.txt

RUN pip install -r /tmp/requirements.txt

ENV CAPTURE_TELEMETRY=1

COPY ./app/models.py /tmp/models.py

# cache the models
RUN python3 /tmp/models.py

COPY ./app /app

COPY ./ui/build /ui

COPY ./run.sh /app/run.sh

WORKDIR /app

VOLUME [ "/opt/storage" ]

EXPOSE 80

CMD ./run.sh
