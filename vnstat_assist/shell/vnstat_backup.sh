#!/bin/bash

# 生成时间戳（格式：年月日时分秒）
timestamp=$(date +%Y%m%d%H%M%S)
# 日志目录（容器内路径）
log_dir="/app/log/shell"
# 日志文件名（带时间戳）
log_file="${log_dir}/vnstat_${timestamp}.log"

# 创建日志目录（如果不存在）
mkdir -p "$log_dir" || { echo "无法创建日志目录: $log_dir"; exit 1; }

chmod 755 "$log_dir"
# 同时输出到控制台和日志文件
exec > >(tee -a "$log_file") 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 脚本启动，日志文件: $log_file"

# 默认处理最近1天数据(昨日)
DAYS=1

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case "$1" in
        -days)
            if [[ $2 =~ ^[0-9]+$ ]] && [ $2 -gt 0 ]; then
                DAYS=$2
                shift 2
            else
                echo "[ERROR] 错误：-days 参数需要正整数" >&2
                exit 1
            fi
            ;;
        *)
            echo "[ERROR] 未知参数：$1" >&2
            exit 1
            ;;
    esac
done

# API地址
# ====================== API地址检查 ======================
api_url="${VNSTAT_API_URL}"


if [ -z "${api_url}" ]; then
    echo "[ERROR] 必须通过Docker环境变量配置 API_URL" >&2
    exit 1
fi

if [[ ! "${api_url}" =~ ^http(s)?:// ]]; then
    echo "[ERROR] API_URL 格式无效: ${api_url}" >&2
    exit 2
fi

# ====================== 数据获取 ======================
echo "[INFO] 正在从API获取数据: $api_url"
if ! api_response=$(curl -sSf "$api_url" 2>/dev/null); then
    echo "[ERROR] API请求失败，请检查：" >&2
    echo "1. 网络连接 | 2. 地址可达性 | 3. 端口开放" >&2
    exit 3
fi

# 创建备份目录
output_dir="/app/backups/json"
mkdir -p "$output_dir"

# 批量处理最近N天数据
for ((i=0; i<DAYS; i++)); do
    # 计算目标日期
    target_day=$(date -d "today - $((i+1)) days" +"%Y%m%d")
    echo "[PROCESSING] 处理日期: $target_day"
    
    # 提取日期组件
    y_year=$(date -d "$target_day" +"%Y")
    y_month=$(date -d "$target_day" +"%m")
    y_day=$(date -d "$target_day" +"%d")

    # 使用jq进行数据过滤
    processed_json=$(jq --arg y_year "$y_year" \
                        --arg y_month "$y_month" \
                        --arg y_day "$y_day" '
        .interfaces |= map(
            .traffic |= (
                if has("fiveminute") then 
                    .fiveminute |= map(select(
                        .date.year == ($y_year | tonumber) and
                        .date.month == ($y_month | tonumber) and
                        .date.day == ($y_day | tonumber)
                    )) 
                else . end |
                
                if has("hour") then 
                    .hour |= map(select(
                        .date.year == ($y_year | tonumber) and
                        .date.month == ($y_month | tonumber) and
                        .date.day == ($y_day | tonumber)
                    )) 
                else . end |
                
                if has("day") then 
                    .day |= map(select(
                        .date.year == ($y_year | tonumber) and
                        .date.month == ($y_month | tonumber) and
                        .date.day == ($y_day | tonumber)
                    )) 
                else . end |
                
                if has("month") then 
                    .month |= map(select(
                        .date.year == ($y_year | tonumber) and
                        .date.month == ($y_month | tonumber)
                    )) 
                else . end |
                
                if has("year") then 
                    .year |= map(select(
                        .date.year == ($y_year | tonumber)
                    )) 
                else . end |
                
                if has("top") then 
                    .top |= map(select(
                        .date.year == ($y_year | tonumber) and
                        .date.month == ($y_month | tonumber) and
                        .date.day == ($y_day | tonumber)
                    )) 
                else . end
            )
        )
    ' <<< "$api_response")

    # 保存结果文件
    output_file="${output_dir}/vnstat_${target_day}.json"
    echo "$processed_json" > "$output_file"
	echo "[SUCCESS] 数据已保存: $output_file"
done

echo "操作完成！已保存最近 ${DAYS} 天数据至：$output_dir"