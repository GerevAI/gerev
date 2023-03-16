# gerev
gerev is a open-source workplace search engine, it's most easily described as _"Google for your company"_.


add image:

![gerev](./images/MegaCard.png)


## Integrations
 - [x] Slack
 - [x] Confluence
 - [x] Google Docs
 - [ ] Notion (In Progress...)
 - [ ] Google Sheets (Coming Soon...)
 - [ ] Google Slides (Coming Soon...)
 - [ ] Google Calendar (Coming Soon...)


## Installation

Install nvidia container toolkit on the host machine.

```
distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
   && curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add - \
   && curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
   
sudo apt-get update

sudo apt-get install -y nvidia-docker2

sudo systemctl restart docker
```


Then run the docker container like so:

```bash
sudo docker run --gpus all -p 80:80 gerev/gerev:0.0.1
```