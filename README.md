# vnstat_dashboard

基于vnStat的实时流量监控面板，提供图表展示

## 🙏 致谢

特别感谢 [hulxv/vnstat-client](https://github.com/hulxv/vnstat-client) 项目的UI设计参考

## 🔧 部署说明

### 安装[vnStat](https://github.com/vergoh/vnstat)

### API配置要求

```
替换vnStatApi为对应vnstat api 一般为host:8685/json.cgi
```

### nginx配置查考

```json
location /traffic/ {
    alias /var/www/html/;
    index vnstat_web.html;
    try_files $uri $uri/ /traffic/vnstat_web.html;
}
```

## 🧩界面截图

![1](screenshots/1.png)

![2](screenshots/2.png)

![2](screenshots/3.png)
