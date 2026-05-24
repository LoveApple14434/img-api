#!/bin/bash

# 查找包含"pexels-image"的进程，排除grep进程本身
ps aux | grep "pexels-image" | grep -v grep | while read line
do
    # 提取进程ID
    pid=$(echo $line | awk '{print $2}')
    
    # 提取进程命令（用于显示）
    cmd=$(echo $line | awk '{print $11}')
    
    # 杀死进程
    echo "Killing process $pid: $cmd"
    kill -9 $pid 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "Successfully killed process $pid"
    else
        echo "Failed to kill process $pid"
    fi
done

# 如果没有找到进程
if ! ps aux | grep -q "pexels-image" | grep -v grep; then
    echo "Now no processes found containing 'pexels-image'"
fi

nohup /usr/bin/python3 /home/Harry/program/image-api/api.py > /home/Harry/program/image-api/logs/api.log 2>&1 &
