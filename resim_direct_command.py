#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Resim 直接命令发送工具
用于发送原始命令字节到Resim
"""

import socket
import struct
import time
import binascii
import logging
import sys

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ResimDirectCommand")

# Resim配置
RESIM_IP = "127.0.0.1"
RESIM_PORT = 20001  # Resim接收命令的端口

def send_raw_bytes(data, ip=RESIM_IP, port=RESIM_PORT):
    """
    发送原始字节到Resim
    
    参数:
        data (bytes): 要发送的字节数据
        ip (str): 目标IP
        port (int): 目标端口
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(data, (ip, port))
        sock.close()
        
        # 记录发送的数据
        hex_data = binascii.hexlify(data).decode()
        logger.info(f"已发送数据到 {ip}:{port}: {hex_data}")
        return True
    except Exception as e:
        logger.error(f"发送数据失败: {e}")
        return False

def send_command(prefix, agent_id=10, direction=0, mode=1):
    """
    发送带有指定前缀的车道变更命令
    
    参数:
        prefix (bytes): 命令前缀
        agent_id (int): 车辆ID
        direction (int): 方向 (0=左, 1=右)
        mode (int): 模式 (0=检查风险, 1=强制变道)
    """
    command = prefix + struct.pack('<iii', agent_id, direction, mode)
    logger.info(f"发送命令: 前缀={prefix}, 车辆ID={agent_id}, 方向={direction}, 模式={mode}")
    return send_raw_bytes(command)

def main():
    """主函数"""
    # 测试前缀列表
    prefixes = [
        (b'CL', "标准车道变更"),
        (b'CAL', "分配车道变更"),
        (b'ACL', "替代前缀1"),
        (b'RCL', "替代前缀2"),
        (b'CCL', "替代前缀3"),
        (b'FCL', "替代前缀4"),
        (b'CCFL', "替代前缀5"),
        (b'C', "单字符前缀"),
        (b'CS', "开始模拟")
    ]
    
    # 解析命令行参数
    if len(sys.argv) > 1:
        try:
            # 如果提供了索引，只发送特定前缀
            idx = int(sys.argv[1]) - 1
            if 0 <= idx < len(prefixes):
                prefix, desc = prefixes[idx]
                logger.info(f"发送 {desc} 命令 (前缀: {prefix})")
                
                # 发送命令
                if prefix == b'CS':
                    # 开始模拟只需要发送前缀
                    send_raw_bytes(prefix)
                else:
                    # 车道变更命令需要附加参数
                    send_command(prefix)
            else:
                logger.error(f"索引必须在1到{len(prefixes)}之间")
        except ValueError:
            logger.error("参数必须是数字")
    else:
        # 无参数时，发送所有命令
        logger.info("逐一发送所有命令前缀...")
        
        # 先发送开始模拟命令
        logger.info("发送开始模拟命令")
        send_raw_bytes(b'CS')
        time.sleep(1)
        
        for i, (prefix, desc) in enumerate(prefixes):
            if prefix == b'CS':
                continue  # 已经发送过了
                
            logger.info(f"{i+1}/{len(prefixes)-1} - 发送 {desc} 命令 (前缀: {prefix})")
            
            # 发送命令
            send_command(prefix)
            
            # 等待一秒
            time.sleep(1)
            
    logger.info("所有命令已发送")

if __name__ == "__main__":
    main() 