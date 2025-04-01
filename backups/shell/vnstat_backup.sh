#!/bin/bash

# 获取昨日日期信息
yesterday=$(date -d "yesterday" +"%Y-%m-%d")
y_year=$(date -d "yesterday" +"%Y")
y_month=$(date -d "yesterday" +"%m")
y_day=$(date -d "yesterday" +"%d")

# API地址
api_url="http://192.168.31.173:19327/vnstat/json.cgi"

# 获取原始JSON数据
if ! api_response=$(curl -sSf "$api_url" 2>/dev/null); then
    echo "错误：无法获取API数据，请检查网络连接或API地址"
    exit 1
fi

# 使用jq处理数据
processed_json=$(jq --arg y_year "$y_year" \
                    --arg y_month "$y_month" \
                    --arg y_day "$y_day" '
    .interfaces |= map(
        .traffic as $traffic |
        .traffic = (
            $traffic |
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

# 保存结果到文件
output_file="/data/vnstat_backup/json/vnstat_${yesterday}.json"
echo "$processed_json" > "$output_file"

echo "成功保存昨日数据到：$output_file"