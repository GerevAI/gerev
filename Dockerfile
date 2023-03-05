FROM python:3.9

COPY ./backend/requirements.txt /tmp/requirements.txt

RUN pip install -r /tmp/requirements.txt