FROM python:3.9

RUN pip install torch

COPY ./backend/requirements.txt /tmp/requirements.txt

RUN pip install -r /tmp/requirements.txt

COPY ./backend/models.py /tmp/models.py

# cache the models
RUN python3 /tmp/models.py

COPY ./backend /app

COPY ./ui/build /ui


CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
