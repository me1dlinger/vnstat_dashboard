# vnstat_dashboard

基于 vnStat Api 的实时流量监控面板，提供图表展示

## 🙏 致谢

特别感谢 [hulxv/vnstat-client](https://github.com/hulxv/vnstat-client) 项目的 UI 设计参考

## 🔧 部署说明

### 安装[vnStat](https://github.com/vergoh/vnstat)

### API 配置要求

```
替换assistApi为工具容器的接口服务
```

### VNSTAT 历史数据备份

由于 vnstat 的 api 能够返回的历史日期数据是有限的，所以写了个定时脚本用于定时请求 vnstat api 备份数据

提供简易 python 服务能够请求指定日期的备份数据

同时实现了账号密码 token 验证，作为统一入口，防止未授权查看统计数据

文件结构

```
vnstat-assist ->备份操作文件夹
  -shell
    -vnstat_backup.sh ->请求接口并保存昨天数据的脚本
  -api
    -api_server.py ->python api服务，获取本地文件并响应
  -docker
    -Dockerfile
    -docker-compose.yml
```

#### TODO:vnstat api 获取不到对应范围的数据时候调用备份数据接口展示

### nginx 配置参考

```
#vnstat可视化页面
location /traffic/ {
    alias /var/www/html/;
    index vnstat_web.html;
    try_files $uri $uri/ /traffic/vnstat_web.html;
}
# 统一API入口
location ~ ^/assist-vnstat(/.*)$ {
    # 统一去除前缀
    rewrite ^/assist-vnstat(/.*)$ $1 break;
    # 代理到后端
    proxy_pass host;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## 🧩 界面截图

![1](screenshots/1.png)

![2](screenshots/2.png)

![2](screenshots/3.png)
