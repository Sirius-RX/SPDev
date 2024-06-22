#!/bin/bash

# 获取脚本所在目录
script_dir=$(dirname "$0")

# 源文件夹路径
source_folder="$script_dir/../SPDev"

echo "Source folder is $source_folder"

# 执行命令并将输出保存到变量
output=$(pip show qcodes_contrib_drivers)

# 使用grep和awk提取Location字段的值
location=$(echo "$output" | grep -oP 'Location: \K.*')

# 输出提取到的Location
echo "qcodes_contrib_drivers的安装位置是: $location/qcodes_contrib_drivers"

# 目标文件夹路径
destination_folder="$location/qcodes_contrib_drivers/drivers"

# 执行拷贝操作

cp -r "$source_folder" "$destination_folder"

echo "已将SPDev文件夹拷贝到$destination_folder目录下。"
