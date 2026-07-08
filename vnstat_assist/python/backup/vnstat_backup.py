import os
import sys
import json
import logging
import argparse
import re
import calendar
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import requests
from dateutil import tz

JSON_DIR = "/app/backups/json"


def get_month_dir(base_dir: str, year: int, month: int) -> str:
    month_str = f"{year}{month:02d}"
    return os.path.join(base_dir, month_str)


def ensure_month_dir(base_dir: str, year: int, month: int) -> str:
    d = get_month_dir(base_dir, year, month)
    os.makedirs(d, exist_ok=True)
    return d


def setup_logging(log_dir: str) -> str:
    os.makedirs(log_dir, exist_ok=True)
    os.chmod(log_dir, 0o755)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    log_file = os.path.join(log_dir, f"vnstat_{timestamp}.log")

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
    )
    return log_file


def parse_args() -> int:
    parser = argparse.ArgumentParser(description="处理vnstat数据")
    parser.add_argument(
        "-days", type=int, default=1, help="处理最近N天的数据（默认1天）"
    )
    args = parser.parse_args()

    if args.days <= 0:
        logging.error("错误：-days 参数需要正整数")
        sys.exit(1)

    return args.days


def fetch_api_data(api_url: str) -> Dict[str, Any]:
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


def filter_data(data: Dict[str, Any], target_date: datetime) -> Dict[str, Any]:
    filtered = {"interfaces": []}

    target_year = target_date.year
    target_month = target_date.month
    target_day = target_date.day

    for interface in data.get("interfaces", []):
        traffic = interface.get("traffic", {})
        new_traffic = {}

        for time_key in ["fiveminute", "hour", "day", "month", "year", "top"]:
            if time_key not in traffic:
                continue

            entries = []
            for entry in traffic[time_key]:
                entry_date = entry.get("date", {})

                if time_key in ["fiveminute", "hour", "top"]:
                    if (
                        entry_date.get("year") == target_year
                        and entry_date.get("month") == target_month
                        and entry_date.get("day") == target_day
                    ):
                        entries.append(entry)
                elif time_key == "day":
                    if (
                        entry_date.get("year") == target_year
                        and entry_date.get("month") == target_month
                        and entry_date.get("day") == target_day
                    ):
                        entries.append(entry)
                elif time_key == "month":
                    if (
                        entry_date.get("year") == target_year
                        and entry_date.get("month") == target_month
                    ):
                        entries.append(entry)
                elif time_key == "year":
                    if entry_date.get("year") == target_year:
                        entries.append(entry)

            if entries:
                new_traffic[time_key] = entries

        if new_traffic:
            new_interface = {k: v for k, v in interface.items() if k != "traffic"}
            new_interface["traffic"] = new_traffic
            filtered["interfaces"].append(new_interface)

    return filtered


def filter_month_data(
    data: Dict[str, Any], target_year: int, target_month: int
) -> Dict[str, Any]:
    filtered = {"interfaces": []}

    for interface in data.get("interfaces", []):
        traffic = interface.get("traffic", {})
        new_traffic = {}

        for time_key in ["fiveminute", "hour", "day", "month", "year", "top"]:
            if time_key not in traffic:
                continue

            entries = []
            for entry in traffic[time_key]:
                entry_date = entry.get("date", {})

                if time_key in ["fiveminute", "hour", "top"]:
                    if (
                        entry_date.get("year") == target_year
                        and entry_date.get("month") == target_month
                    ):
                        entries.append(entry)
                elif time_key == "day":
                    if (
                        entry_date.get("year") == target_year
                        and entry_date.get("month") == target_month
                    ):
                        entries.append(entry)
                elif time_key == "month":
                    if (
                        entry_date.get("year") == target_year
                        and entry_date.get("month") == target_month
                    ):
                        entries.append(entry)
                elif time_key == "year":
                    if entry_date.get("year") == target_year:
                        entries.append(entry)

            if entries:
                new_traffic[time_key] = entries

        if new_traffic:
            new_interface = {k: v for k, v in interface.items() if k != "traffic"}
            new_interface["traffic"] = new_traffic
            filtered["interfaces"].append(new_interface)

    return filtered


def backup_month_data(
    data: Dict[str, Any], target_year: int, target_month: int, output_dir: str
) -> bool:
    month_dir = ensure_month_dir(output_dir, target_year, target_month)
    month_str = f"{target_year}{target_month:02d}"
    month_file = os.path.join(month_dir, f"vnstat_month_{month_str}.json")

    if os.path.exists(month_file):
        logging.info(f"月备份文件已存在，跳过: {month_file}")
        return False

    filtered_data = filter_month_data(data, target_year, target_month)

    has_day_data = False
    for interface in filtered_data.get("interfaces", []):
        if interface.get("traffic", {}).get("day"):
            has_day_data = True
            break

    if not has_day_data:
        logging.warning(
            f"API未返回 {target_year}-{target_month:02d} 的天维度数据，跳过月备份"
        )
        return False

    with open(month_file, "w") as f:
        json.dump(filtered_data, f, indent=2)
    logging.info(f"月备份数据已保存: {month_file}")
    return True


def merge_day_backups_to_month(
    output_dir: str, target_year: int, target_month: int
) -> Optional[Dict[str, Any]]:
    days_in_month = calendar.monthrange(target_year, target_month)[1]
    day_files_data: List[Dict[str, Any]] = []

    month_dir = get_month_dir(output_dir, target_year, target_month)

    for day in range(1, days_in_month + 1):
        day_str = f"{target_year}{target_month:02d}{day:02d}"
        day_file = os.path.join(month_dir, f"vnstat_{day_str}.json")

        if os.path.isfile(day_file):
            try:
                with open(day_file, "r") as f:
                    day_data = json.load(f)
                day_files_data.append(day_data)
            except (json.JSONDecodeError, Exception) as e:
                logging.warning(f"读取天备份文件失败 {day_file}: {str(e)}")

    if not day_files_data:
        logging.warning(f"未找到 {target_year}-{target_month:02d} 的任何天备份文件")
        return None

    merged: Dict[str, Any] = {"interfaces": []}
    interface_map: Dict[str, Dict[str, Any]] = {}

    for day_data in day_files_data:
        for interface in day_data.get("interfaces", []):
            iface_name = interface.get("name", "unknown")
            if iface_name not in interface_map:
                interface_map[iface_name] = {
                    "name": iface_name,
                    "alias": interface.get("alias", ""),
                    "created": interface.get("created"),
                    "updated": interface.get("updated"),
                    "traffic": {
                        "day": [],
                        "month": [],
                    },
                }

            iface = interface_map[iface_name]
            traffic = interface.get("traffic", {})

            for entry in traffic.get("day", []):
                iface["traffic"]["day"].append(entry)

            for entry in traffic.get("month", []):
                existing = iface["traffic"]["month"]
                entry_date = entry.get("date", {})
                is_dup = False
                for ex in existing:
                    ex_date = ex.get("date", {})
                    if ex_date.get("year") == entry_date.get("year") and ex_date.get("month") == entry_date.get("month"):
                        is_dup = True
                        break
                if not is_dup:
                    iface["traffic"]["month"].append(entry)

    for iface_name, iface_data in interface_map.items():
        iface_data["traffic"]["day"].sort(key=lambda x: x.get("timestamp", 0))

        if not iface_data["traffic"]["month"]:
            total_rx = sum(d.get("rx", 0) for d in iface_data["traffic"]["day"])
            total_tx = sum(d.get("tx", 0) for d in iface_data["traffic"]["day"])
            first_day_ts = None
            for d in iface_data["traffic"]["day"]:
                d_date = d.get("date", {})
                if (
                    d_date.get("year") == target_year
                    and d_date.get("month") == target_month
                    and d_date.get("day") == 1
                ):
                    first_day_ts = d.get("timestamp")
                    break
            if first_day_ts is None and iface_data["traffic"]["day"]:
                first_day_ts = iface_data["traffic"]["day"][0].get("timestamp")

            iface_data["traffic"]["month"] = [
                {
                    "id": 0,
                    "date": {"year": target_year, "month": target_month},
                    "timestamp": first_day_ts or 0,
                    "rx": total_rx,
                    "tx": total_tx,
                }
            ]

        merged["interfaces"].append(iface_data)

    return merged


def organize_backup_files(base_dir: str):
    if not os.path.isdir(base_dir):
        logging.info(f"备份目录不存在，跳过整理: {base_dir}")
        return

    day_pattern = re.compile(r"^vnstat_(\d{4})(\d{2})(\d{2})\.json$")
    month_pattern = re.compile(r"^vnstat_month_(\d{4})(\d{2})\.json$")

    moved_count = 0
    for filename in os.listdir(base_dir):
        filepath = os.path.join(base_dir, filename)
        if not os.path.isfile(filepath):
            continue

        m = day_pattern.match(filename)
        if m:
            year, month = int(m.group(1)), int(m.group(2))
            month_dir = ensure_month_dir(base_dir, year, month)
            dest = os.path.join(month_dir, filename)
            if not os.path.exists(dest):
                os.rename(filepath, dest)
                moved_count += 1
                logging.info(f"整理: {filename} -> {month_dir}")
            else:
                os.remove(filepath)
                logging.info(f"整理: 目标已存在，删除源文件 {filename}")
            continue

        m = month_pattern.match(filename)
        if m:
            year, month = int(m.group(1)), int(m.group(2))
            month_dir = ensure_month_dir(base_dir, year, month)
            dest = os.path.join(month_dir, filename)
            if not os.path.exists(dest):
                os.rename(filepath, dest)
                moved_count += 1
                logging.info(f"整理: {filename} -> {month_dir}")
            else:
                os.remove(filepath)
                logging.info(f"整理: 目标已存在，删除源文件 {filename}")
            continue

    logging.info(f"备份文件整理完成，共移动 {moved_count} 个文件")


def main():
    for handler in logging.root.handlers[:]:
        handler.close()
        logging.root.removeHandler(handler)
    log_dir = "/app/log"
    log_file = setup_logging(log_dir)
    logging.info(f"脚本启动，日志文件: {log_file}")

    api_url = os.getenv("VNSTAT_API_URL")
    if not api_url:
        logging.error("必须通过Docker环境变量配置 VNSTAT_API_URL")
        sys.exit(1)

    if not api_url.startswith(("http://", "https://")):
        logging.error(f"API_URL 格式无效: {api_url}")
        sys.exit(2)

    output_dir = JSON_DIR
    today = datetime.now(tz=tz.gettz("Asia/Shanghai"))
    days = parse_args()
    data = fetch_api_data(api_url)

    os.makedirs(output_dir, exist_ok=True)
    os.chmod(output_dir, 0o755)

    for i in range(days):
        target_date = today - timedelta(days=i + 1)
        handle_date = target_date.strftime("%Y%m%d")
        logging.info(f"处理日期: {handle_date}")

        month_dir = ensure_month_dir(output_dir, target_date.year, target_date.month)
        output_file = os.path.join(month_dir, f"vnstat_{handle_date}.json")

        if os.path.exists(output_file):
            logging.info(f"天备份文件已存在，跳过: {output_file}")
            continue

        filtered_data = filter_data(data, target_date)
        with open(output_file, "w") as f:
            json.dump(filtered_data, f, indent=2)
        logging.info(f"数据已保存: {output_file}")

    logging.info(f"操作完成！已保存最近 {days} 天数据至：{output_dir}")


def backup_last_month():
    for handler in logging.root.handlers[:]:
        handler.close()
        logging.root.removeHandler(handler)
    log_dir = "/app/log"
    log_file = setup_logging(log_dir)
    logging.info(f"月备份脚本启动，日志文件: {log_file}")

    api_url = os.getenv("VNSTAT_API_URL")
    if not api_url:
        logging.error("必须通过Docker环境变量配置 VNSTAT_API_URL")
        sys.exit(1)

    if not api_url.startswith(("http://", "https://")):
        logging.error(f"API_URL 格式无效: {api_url}")
        sys.exit(2)

    output_dir = JSON_DIR
    os.makedirs(output_dir, exist_ok=True)
    os.chmod(output_dir, 0o755)

    today = datetime.now(tz=tz.gettz("Asia/Shanghai"))
    last_month_date = today.replace(day=1) - timedelta(days=1)
    target_year = last_month_date.year
    target_month = last_month_date.month

    month_dir = ensure_month_dir(output_dir, target_year, target_month)
    month_str = f"{target_year}{target_month:02d}"
    month_file = os.path.join(month_dir, f"vnstat_month_{month_str}.json")

    if os.path.exists(month_file):
        logging.info(f"上月备份文件已存在，跳过: {month_file}")
        return

    logging.info(f"开始备份上月数据: {target_year}-{target_month:02d}")

    data = fetch_api_data(api_url)
    backup_month_data(data, target_year, target_month, output_dir)


if __name__ == "__main__":
    main()
