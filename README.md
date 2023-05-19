[⚡🔎 Live online demo!](https://demo.gerev.ai)  
# AI-powered enterprise search engine 🔎

### Join Discord for early access code!
[![Discord Follow](https://dcbadge.vercel.app/api/server/7hNdF7yu8r?style=flat)](https://discord.gg/7hNdF7yu8r)
[![DockerHub Pulls][docker-pull-img]][docker-pull]


[docker-pull]: https://hub.docker.com/r/gerev/gerev
[docker-pull-img]: https://img.shields.io/docker/pulls/gerev/gerev.svg

[Join here!](https://discord.gg/NKhTX7JZAF)

# Search engine for your organization!
![first image](./images/api.gif)
**Find any conversation, doc, or internal page in seconds**  ⏲️⚡️  
**Join 100+** devs by hosting your own gerev instance, become a **hero** within your org! 💪

<!--ts-->
   * [Integrations](#integrations)
   * [Getting Started](#getting-started)
      * [Cloud](#managed-cloud-pro)
      * [Self-Hosted](#self-hosted-community)
<!--te-->

## Made for help desk techies 👨‍💻
### Troubleshoot Issues 🐛
![fourth image](./images/sql-card.png)

### Or find internal issues _fast_ ⚡️
![second image](./images/product-example.png)


Integrations
============
 - [x] Slack
 - [x] Confluence
 - [X] Jira
 - [x] Google Drive (Docs, .docx, .pptx) - by [@bary12](https://github.com/bary12) :pray: 
 - [X] Confluence Cloud - by [@bryan-pakulski](https://github.com/bryan-pakulski) :pray: 
 - [X] Bookstack - by [@flifloo](https://github.com/flifloo) :pray:
 - [X] Mattermost - by [@itaykal](https://github.com/Itaykal) :pray:
 - [X] RocketChat - by [@flifloo](https://github.com/flifloo) :pray:
 - [X] Gitlab Issues - by [@eran1232](https://github.com/eran1232) :pray:
 - [ ] Zendesk (In PR :pray:)
 - [ ] Stackoverflow Teams (In PR :pray:)
 - [ ] Azure DevOps (In PR :pray:)
 - [ ] Phabricator (In PR :pray:)
 - [ ] Trello (In PR... :pray:)
 - [ ] Notion (In Progress... :pray:)
 - [ ] Asana
 - [ ] Sharepoint
 - [ ] Box
 - [ ] Dropbox
 - [ ] Github Enterprise
 - [ ] Microsoft Teams

 
:pray:  - by the community 

## Add your own data source NOW 🚀
See the full guide at [ADDING-A-DATA-SOURCE.md](./ADDING-A-DATA-SOURCE.md).


## Natural Language
Enables searching using natural language. such as `"How to do X"`, `"how to connect to Y"`, `"Do we support Z"`

---  

Getting Started
============
## Managed Cloud (Pro)  
[Let's talk](https://calendly.com/mrdotcom/demo)  
- [X] Authentication
- [X] Multiple Users
- [X] GPU machine
- [X] 24/7 Support
- Self hosted version (with multi-user also supported)
  
## Self-hosted (Community)
1. Install *Nvidia for docker* (on host that runs the docker runtime)
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

## Run from source 
See [ADDING-A-DATA-SOURCE.md](./ADDING-A-DATA-SOURCE.md) in the Setup development environment section.
  
  
- **gerev is also popular with some big names. 😉**  

---  

![first image](./images/bill.png)

Built by the community 💜

<a href = "https://github.com/Tanu-N-Prabhu/Python/graphs/contributors">
  <img src = "https://contrib.rocks/image?repo=gerevai/gerev"/>
</a>

Made with [contributors-img](https://contrib.rocks).
