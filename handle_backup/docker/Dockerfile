FROM debian:12-slim

# 创建并配置阿里云镜像源
RUN echo "deb http://mirrors.aliyun.com/debian/ bookworm main non-free contrib" > /etc/apt/sources.list && \
  echo "deb http://mirrors.aliyun.com/debian/ bookworm-updates main non-free contrib" >> /etc/apt/sources.list && \
  echo "deb http://mirrors.aliyun.com/debian-security bookworm-security main" >> /etc/apt/sources.list

# 安装依赖
RUN apt-get update && apt-get install -y \
  curl \
  jq \
  cron \
  tzdata \
  python3 \
  && rm -rf /var/lib/apt/lists/*

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime

# 创建目录结构
RUN mkdir -p /data/vnstat_backup/{shell,json,api}
# 复制脚本和API文件
COPY shell/vnstat_backup.sh /data/vnstat_backup/shell/
COPY api/api_server.py /data/vnstat_backup/api/

# 设置定时任务
RUN chmod +x /data/vnstat_backup/shell/vnstat_backup.sh \
  && chmod +x  /data/vnstat_backup/api/api_server.py 

# 配置cron任务
RUN echo "0 1 * * * root /data/vnstat_backup/shell/vnstat_backup.sh" > /etc/cron.d/vnstat-backup


EXPOSE 19328

# 启动命令
CMD bash -c "service cron start && cd /data/vnstat_backup/api && python3 api_server.py"