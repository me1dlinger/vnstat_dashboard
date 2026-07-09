# vnstat_dashboard

<div align="center">

[![中文](https://img.shields.io/badge/中文-README-red)](README.md)
[![English](https://img.shields.io/badge/English-README-blue)](README_EN.md)
<br>
[![Docker](https://img.shields.io/docker/pulls/meidlinger1024/vnstat-dashboard?logo=docker)](https://hub.docker.com/r/meidlinger1024/vnstat-dashboard)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL%203.0-4CAF50?style=flat-square)](LICENSE)
</div>


# vnstat_dashboard

Real-time Traffic Monitoring and Statistics Dashboard Based on vnStat API

## 🙏 Acknowledgments

Special thanks to the [hulxv/vnstat-client](https://github.com/hulxv/vnstat-client) project for UI design reference.

## 🔰 Features

### Page Display

- Usage statistics cards
- Network interface data switching
- Multi-dimensional traffic usage statistics
- Line chart/table view switching
- Automatic unit switching for traffic usage
- Custom theme configuration

### VNSTAT Historical Data Backup

Since the vnstat API has limited historical data retention, we implemented a scheduled backup script:
- Automatically backs up previous day's data at 01:00 daily
- Preserves complete historical records
- Configurable backup data usage in the interface

### Page Access Authentication

Enable authentication for public network access

### File Structure

```
vnstat_assist
├── python
│   ├── api
│   │   ├── api_server.py               ➔ API service
│   │   ├── templates
│   │   │   └── index.html              ➔ vnstat dashboard panel
│   │   └── static                      ➔ Static files directory
│   │       ├── css
│   │       │   ├── all.min.css         ➔ Font-awesome styles
│   │       │   └── styles.css          ➔ Custom CSS styles
│   │       ├── js
│   │       │   ├── apexcharts.js
│   │       │   └── vue.js
│   │       ├── webfonts
│   │       │   └── fa-solid-900.woff2  ➔ Font-awesome webfont
│   │       └── favicon.png             ➔ Website favicon
│   ├── backup
│   │   ├── task_scheduler.py           ➔ Timed backup executor
│   │   └── vnstat_backup.py            ➔ vnstat data backup implementation
│   └── requirements.txt                ➔ Python dependencies
├── conf
│   └── supervisord.conf                ➔ Process management configuration
├── Dockerfile                          ➔ Docker build configuration
└── docker-compose.yml                  ➔ Docker compose config (requires pre-existing host directories)
```

## 🔧 Deployment

### Install [vnStat](https://github.com/vergoh/vnstat)

### Verify API accessibility: Access `http://[server]:[port]/json.cgi` to ensure JSON response

### Pull Docker Image

```
docker pull meidlinger1024/vnstat-dashboard:latest
```
### Docker Run Configuration

```

docker run -d \
  --name vnstat-dashboard \
  -p 19328:19328 \
  -v ${path-on-host}/log:/app/log \
  -v ${path-on-host}/backups:/app/backups \
  -e VNA_AUTH_ENABLE=1 \
  -e VNSTAT_API_URL=http://${host}:${port}/json.cgi \
  -e VNA_SECRET_KEY=${secret_key} \
  -e VNA_EXPIRE_SECONDS=3600 \
  -e VNA_USERNAME=${username} \
  -e VNA_PASSWORD=${password} \
  vnstat-dashboard:latest
```

### Docker Compose Configuration
```
version: '3'
services:
  vnstat-dashboard:
    image: vnstat-dashboard:latest
    container_name: vnstat-dashboard
    restart: always
    ports:
      - "19328:19328"
    volumes:
        # Specify host machine paths (create them first if needed)
      - ${path-on-host}/log:/app/log
      - ${path-on-host}/backups:/app/backups
    environment:
      # Enable authentication
      - VNA_AUTH_ENABLE=1
      # vnStat JSON API endpoint 
      - VNSTAT_API_URL=http://${host}:${port}/json.cgi
      # Authentication secret key
      - VNA_SECRET_KEY=${secret_key}
      # Token expiration time (seconds)
      - VNA_EXPIRE_SECONDS=3600
      # Authentication username
      - VNA_USERNAME=${username}
      # Authentication password
      - VNA_PASSWORD=${password}
```

## 🧩 Screenshots

![1](https://files.seeusercontent.com/2026/07/09/gQs3/1.png)

![2](https://files.seeusercontent.com/2026/07/09/rZj7/2.png)

![3](https://files.seeusercontent.com/2026/07/09/fW5w/3.png)

![4](https://files.seeusercontent.com/2026/07/09/n6Ko/4.png)

![5](https://files.seeusercontent.com/2026/07/09/xrD8/5.png)

![6](https://files.seeusercontent.com/2026/07/09/jDg0/6.png)

![7](https://files.seeusercontent.com/2026/07/09/A8rq/7.png)
