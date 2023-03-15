FROM python:3.9

RUN pip install torch

COPY ./app/requirements.txt /tmp/requirements.txt

RUN pip install -r /tmp/requirements.txt

COPY ./app/models.py /tmp/models.py

# cache the models
RUN python3 /tmp/models.py

COPY ./app /app

COPY ./ui/build /ui

WORKDIR /app

VOLUME [ "/opt/storage" ]

EXPOSE 80

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
