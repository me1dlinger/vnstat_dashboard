import os
import sys
import json
import logging
import argparse
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any
import requests
from dateutil import tz  # 需要安装python3-dateutil

# 配置日志
def setup_logging(log_dir: str) -> str:
    """初始化日志配置，返回日志文件路径"""
    os.makedirs(log_dir, exist_ok=True)
    os.chmod(log_dir, 0o755)  # 确保日志目录可访问
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    log_file = os.path.join(log_dir, f"vnstat_{timestamp}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return log_file

# 解析命令行参数
def parse_args() -> int:
    """解析命令行参数，返回天数"""
    parser = argparse.ArgumentParser(description="处理vnstat数据")
    parser.add_argument("-days", type=int, default=1,
                        help="处理最近N天的数据（默认1天）")
    args = parser.parse_args()
    
    if args.days <= 0:
        logging.error("错误：-days 参数需要正整数")
        sys.exit(1)
    
    return args.days

# 获取API数据
def fetch_api_data(api_url: str) -> Dict[str, Any]:
    """从API获取JSON数据"""
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"API请求失败: {str(e)}")
        sys.exit(3)
    except json.JSONDecodeError:
        logging.error("API返回无效的JSON数据")
        sys.exit(4)

# 过滤数据
def filter_data(data: Dict[str, Any], target_date: datetime) -> Dict[str, Any]:
    """按日期过滤数据（替代原jq逻辑）"""
    filtered = {"interfaces": []}
    
    target_year = target_date.year
    target_month = target_date.month
    target_day = target_date.day
    
    for interface in data.get("interfaces", []):
        traffic = interface.get("traffic", {})
        new_traffic = {}
        
        # 过滤各时间粒度的数据
        for time_key in ["fiveminute", "hour", "day", "month", "year", "top"]:
            if time_key not in traffic:
                continue
                
            entries = []
            for entry in traffic[time_key]:
                entry_date = entry.get("date", {})
                
                # 根据时间粒度匹配
                if time_key in ["fiveminute", "hour", "top"]:
                    if (entry_date.get("year") == target_year and
                        entry_date.get("month") == target_month and
                        entry_date.get("day") == target_day):
                        entries.append(entry)
                elif time_key == "day":
                    if (entry_date.get("year") == target_year and
                        entry_date.get("month") == target_month and
                        entry_date.get("day") == target_day):
                        entries.append(entry)
                elif time_key == "month":
                    if (entry_date.get("year") == target_year and
                        entry_date.get("month") == target_month):
                        entries.append(entry)
                elif time_key == "year":
                    if entry_date.get("year") == target_year:
                        entries.append(entry)
            
            if entries:
                new_traffic[time_key] = entries
        
        if new_traffic:
            new_interface = interface.copy()
            new_interface["traffic"] = new_traffic
            filtered["interfaces"].append(new_interface)
    
    return filtered

"""
vnstat_backup.py - 替代原Shell脚本的Python版本
功能：从API获取vnstat数据，按日期过滤并保存为JSON文件，自动备份旧文件
"""

# 主逻辑
def main():
    # 初始化日志（保持原有代码不变）
    for handler in logging.root.handlers[:]:
        handler.close()
        logging.root.removeHandler(handler)
    log_dir = "/app/log/python"
    log_file = setup_logging(log_dir)
    logging.info(f"脚本启动，日志文件: {log_file}")

    # 检查API_URL（保持原有代码不变）
    api_url = os.getenv("VNSTAT_API_URL")
    if not api_url:
        logging.error("必须通过Docker环境变量配置 VNSTAT_API_URL")
        sys.exit(1)
    
    if not api_url.startswith(("http://", "https://")):
        logging.error(f"API_URL 格式无效: {api_url}")
        sys.exit(2)

    # 处理数据（添加备份目录创建）
    output_dir = "/app/backups/json"
    backup_root = os.path.join(output_dir, "backup")
    today =  datetime.now(tz=tz.gettz("Asia/Shanghai"))
    days = parse_args()
    data = fetch_api_data(api_url)
    # 创建输出目录和备份目录
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(backup_root, exist_ok=True)
    os.chmod(output_dir, 0o755)
    os.chmod(backup_root, 0o755)

    for i in range(days):
        target_date = today - timedelta(days=i+1)
        handle_date =  target_date.strftime('%Y%m%d')
        logging.info(f"处理日期: {handle_date}")
        filtered_data = filter_data(data, target_date)
        output_file = os.path.join(
            output_dir,
            f"vnstat_{handle_date}.json"
        )
        # 备份已存在的文件
        if os.path.exists(output_file):
            try:
                backup_timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                backup_dir = os.path.join(backup_root, backup_timestamp)
                os.makedirs(backup_dir, exist_ok=True)
                os.chmod(backup_dir, 0o755)
                backup_file = os.path.join(backup_dir, os.path.basename(output_file))
                shutil.move(output_file, backup_file)
                logging.info(f"已备份旧文件至: {backup_file}")
            except Exception as e:
                logging.error(f"文件备份失败: {str(e)}")
                logging.error("为避免数据丢失，跳过本次保存")
                continue  # 跳过当前文件的保存

        # 保存新文件
        with open(output_file, "w") as f:
            json.dump(filtered_data, f, indent=2)
        logging.info(f"数据已保存: {output_file}")
    
    logging.info(f"操作完成！已保存最近 {days} 天数据至：{output_dir}")

if __name__ == "__main__":
    main()