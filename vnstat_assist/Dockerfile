FROM python:3.9-slim

# 在 sources.list 中补全 security 源
RUN echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bullseye main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
  echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bullseye-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
  echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bullseye-backports main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
  echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bullseye-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

# 安装依赖
RUN apt-get update && apt-get install -y \
  curl \
  jq \
  cron \
  tzdata \
  nginx  \
  supervisor  \
  procps \
  net-tools \
  && rm -rf /var/lib/apt/lists/*

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime

# 创建目录结构
RUN mkdir -p /app/shell
RUN mkdir -p /api
RUN mkdir -p /www
RUN mkdir -p /backups
RUN mkdir -p /log/nginx
RUN mkdir -p /log/shell

# 复制脚本和API文件
COPY shell /app/shell
COPY api /app/api
COPY www /app/www
COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY conf/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

RUN chmod +x /app/shell/vnstat_backup.sh \
  && chmod +x /app/api/api_server.py 

RUN pip install --no-cache-dir -r /app/api/requirements.txt


# 设置定时任务
RUN echo "0 1 * * * root /app/shell/vnstat_backup.sh" > /etc/cron.d/vnstat-backup

EXPOSE 80

# 启动命令
CMD ["supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]