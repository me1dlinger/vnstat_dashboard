#!/bin/bash

# 默认处理最近1天数据
DAYS=1

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case "$1" in
        -days)
            if [[ $2 =~ ^[0-9]+$ ]] && [ $2 -gt 0 ]; then
                DAYS=$2
                shift 2
            else
                echo "错误：-days 参数需要正整数" >&2
                exit 1
            fi
            ;;
        *)
            echo "未知参数：$1" >&2
            exit 1
            ;;
    esac
done

# API地址
api_url="http://192.168.31.173:19327/vnstat/json.cgi"

# 获取原始JSON数据
echo "正在获取网络流量数据..."
if ! api_response=$(curl -sSf "$api_url" 2>/dev/null); then
    echo "错误：无法获取API数据，请检查："
    echo "1. 网络连接是否正常"
    echo "2. API地址是否正确: $api_url"
    exit 1
fi

# 创建备份目录
output_dir="/data/vnstat_backup/json"
mkdir -p "$output_dir"

# 批量处理最近N天数据
for ((i=0; i<DAYS; i++)); do
    # 计算目标日期
    target_day=$(date -d "today - $((i+1)) days" +"%Y-%m-%d")
    echo "正在处理 $target_day 数据..."
    
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
done

echo "操作完成！已保存最近 ${DAYS} 天数据至：$output_dir"