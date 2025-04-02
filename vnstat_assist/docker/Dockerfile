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
RUN mkdir -p /data/vnstat-assist/{shell,json,api}
# 复制脚本和API文件
COPY shell/vnstat-assist.sh /data/vnstat-assist/shell/
COPY api/api_server.py /data/vnstat-assist/api/

# 设置定时任务
RUN chmod +x /data/vnstat-assist/shell/vnstat-assist.sh \
  && chmod +x  /data/vnstat-assist/api/api_server.py 

# 配置cron任务
RUN echo "0 1 * * * root /data/vnstat-assist/shell/vnstat-assist.sh" > /etc/cron.d/vnstat-backup


EXPOSE 19328

# 启动命令
CMD bash -c "service cron start && cd /data/vnstat-assist/api && python3 api_server.py"