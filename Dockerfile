FROM postgres:latest

RUN apt-get update

RUN apt-get install -y python3-dev python3-pip

COPY ./backend/requirements.txt /tmp/requirements.txt

RUN pip3 install -r /tmp/requirements.txt