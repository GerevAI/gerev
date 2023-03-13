FROM qdrant/qdrant

RUN apt-get update && apt-get install -y python3 python3-pip

RUN pip install torch

COPY ./app/requirements.txt /tmp/requirements.txt

RUN pip install -r /tmp/requirements.txt

COPY ./app/models.py /tmp/models.py

# cache the models
RUN python3 /tmp/models.py

COPY ./app /app

COPY ./ui/build /ui

COPY ./run.sh /app/run.sh

WORKDIR /app

COPY ./app/.env .env

EXPOSE 80

CMD ["./run.sh"]
