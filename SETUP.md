# Getting Started

============

## Managed Cloud (Pro)

[Sign up Free](https://app.klu.so/signup?utm_source=github_gerevai)

- [x] Authentication
- [x] Multiple Users
- [x] GPU machine
- [x] 24/7 Support
- Self hosted version (with multi-user also supported)

## Self-hosted (Community)

1. Install _Nvidia for docker_ (on host that runs the docker runtime)
2. Run docker

### Nvidia for docker

Install nvidia container toolkit on the host machine.

```
distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
   && curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add - \
   && curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update

sudo apt-get install -y nvidia-docker2

sudo systemctl restart docker
```

### Run docker

Then run the docker container like so:

### Nvidia hardware

```bash
docker run --gpus all --name=gerev -p 80:80 -v ~/.gerev/storage:/opt/storage gerev/gerev
```

### CPU only (no GPU)

```
docker run --name=gerev -p 80:80 -v ~/.gerev/storage:/opt/storage gerev/gerev
```

add `-d` if you want to detach the container.

## Add your own data source NOW 🚀

See the full guide at [ADDING-A-DATA-SOURCE.md](./ADDING-A-DATA-SOURCE.md).

## Run from source

See [ADDING-A-DATA-SOURCE.md](./ADDING-A-DATA-SOURCE.md) in the Setup development environment section.
