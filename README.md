# gerev
A heap of socks. Coming soon...


## Installation

Install nvidia container toolkit on the host

```
distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
   && curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add - \
   && curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
   
sudo apt-get update

sudo apt-get install -y nvidia-docker2

sudo systemctl restart docker
```

build the UI

```
cd ui/
npm install
npm run build
```

Then build and the docker

```
docker build -t gerev .
docker run --volume ~/.gerev/storage:/opt/storage --gpus all -p 0.0.0.0:80:80 gerev
```