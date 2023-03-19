# Gerev - Workplace search for Devs
Tired of searching for that one docuement you know exists somewhere, but not sure exactly where?

![gerev](./images/everything.png)

## Listening?
You should try Gerev out! Gerev allows you to search your entire company from a single place.

## Made for devs
### Find docs
![gerev](./images/product-example.png)

### Find Code
![gerev](./images/CodeCard.png)

### Troubleshoot Issues
![gerev](./images/sql-example.png)

## Integrations
 - [x] Slack
 - [x] Confluence
 - [x] Google Drive
 - [ ] Gitlab Issues (In PR)
 - [ ] Notion (In Progress...)
 - [ ] Microsoft Teams
 - [ ] Sharepoint
 - [ ] OneDrive
 - [ ] Gmail
 - [ ] Wiki Crawler
 
### Natural Langauge
allows searching using natural language. such as "How to do X", "how to connect to Y", "Do we support Z"

## Installation

### Nvidia hardware
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

### Nvidia hardware
```bash
sudo docker run --gpus all -p 80:80 -v ~/.gerev/storage:/opt/storage gerev/gerev
```

### CPU only (no GPU)
```
sudo docker run -p 80:80 -v ~/.gerev/storage:/opt/storage gerev/gerev
```
