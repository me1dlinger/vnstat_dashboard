FROM python:3.9-slim

# 安装依赖
RUN apt-get update && apt-get install -y \
  supervisor  \
  && rm -rf /var/lib/apt/lists/*

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime

# 创建目录结构
RUN mkdir -p /app/python
RUN mkdir -p /app/backups
RUN mkdir -p /app/log/python

# 复制脚本和API文件
COPY /python /app/python
COPY conf/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

RUN chmod +x /app/python/backup/vnstat_backup.py \
  && chmod +x /app/python/backup/task_scheduler.py \
  && chmod +x /app/python/api/api_server.py 

RUN pip install --no-cache-dir -r /app/python/requirements.txt

EXPOSE 19328

# 启动命令
CMD ["supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
