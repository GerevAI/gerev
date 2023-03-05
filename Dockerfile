FROM postgres:latest

RUN apt-get update

RUN apt-get install -y python3-dev python3-pip

