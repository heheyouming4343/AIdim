#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Resim DSMode快速修复和测试工具

此脚本提供两个主要功能：
1. 自动启动Resim并启用DSMode
2. 发送测试UDP命令并监控响应
"""

import os
import sys
import socket
import struct
import time
import subprocess
import logging
import argparse
import binascii

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Resim配置
RESIM_IP = "127.0.0.1"
RESIM_SEND_PORT = 20001
RESIM_RECEIVE_PORT = 20000
RESIM_EXE_PATH = "D:/Reisim_BK_UDP/Reisim.exe"  # 根据实际路径修改
SYS_FILE_PATH = "D:/Reisim_BK_UDP/Lanechange.sysfile"  # 根据实际路径修改

def start_resim_with_dsmode():
    """启动Resim并启用DSMode"""
    cmd = f'"{RESIM_EXE_PATH}" --ds-mode --udp-config="{SYS_FILE_PATH}"'
    logging.info(f"启动Resim: {cmd}")
    
    try:
        # 非阻塞方式启动Resim
        subprocess.Popen(cmd, shell=True)
        logging.info("Resim启动命令已发送")
        time.sleep(5)  # 等待Resim启动
        return True
    except Exception as e:
        logging.error(f"启动Resim失败: {e}")
        return False

def send_udp_packet(data, description):
    """发送UDP数据包并记录日志"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        sock.sendto(data, (RESIM_IP, RESIM_SEND_PORT))
        hex_data = binascii.hexlify(data).decode('utf-8')
        logging.info(f"已发送 {description}: {hex_data}")
        time.sleep(1)  # 等待处理
        return True
    except Exception as e:
        logging.error(f"发送数据失败 - {description}: {e}")
        return False
    finally:
        sock.close()

def test_start_simulation():
    """测试启动模拟命令"""
    logging.info("发送启动模拟命令 (CS)")
    return send_udp_packet(b'CS', "启动模拟命令")

def test_lane_change(agent_id=10, direction=0, force=1):
    """测试换道命令
    
    参数:
        agent_id (int): 车辆ID
        direction (int): 方向 (0=左, 1=右)
        force (int): 模式 (0=检查风险, 1=强制)
    """
    cmd_data = b'CL' + struct.pack('<iii', agent_id, direction, force)
    direction_str = "左" if direction == 0 else "右"
    force_str = "强制" if force == 1 else "安全"
    
    description = f"换道命令 (车辆ID={agent_id}, {direction_str}侧, {force_str}模式)"
    logging.info(f"发送{description}")
    
    return send_udp_packet(cmd_data, description)

def listen_for_responses():
    """监听来自Resim的UDP响应"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2)  # 设置超时
    
    try:
        # 绑定到接收端口
        sock.bind(("0.0.0.0", RESIM_RECEIVE_PORT))
        logging.info(f"监听UDP响应 (端口 {RESIM_RECEIVE_PORT})...")
        
        # 监听10秒
        start_time = time.time()
        while time.time() - start_time < 10:
            try:
                data, addr = sock.recvfrom(1024)
                hex_data = binascii.hexlify(data).decode('utf-8')
                logging.info(f"收到来自 {addr} 的响应: {hex_data}")
            except socket.timeout:
                pass
    except Exception as e:
        logging.error(f"监听错误: {e}")
    finally:
        sock.close()

def main():
    parser = argparse.ArgumentParser(description="Resim DSMode快速修复和测试工具")
    parser.add_argument("--start", action="store_true", help="启动Resim并启用DSMode")
    parser.add_argument("--sim", action="store_true", help="发送启动模拟命令")
    parser.add_argument("--lane", action="store_true", help="发送换道命令")
    parser.add_argument("--listen", action="store_true", help="监听UDP响应")
    parser.add_argument("--all", action="store_true", help="执行所有操作")
    
    args = parser.parse_args()
    
    # 如果没有参数，显示帮助
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    # 执行所有操作
    if args.all:
        args.start = args.sim = args.lane = args.listen = True
    
    # 依次执行请求的操作
    if args.start:
        start_resim_with_dsmode()
    
    if args.sim:
        test_start_simulation()
    
    if args.lane:
        # 测试左侧强制换道
        test_lane_change(agent_id=10, direction=0, force=1)
        time.sleep(1)
        # 测试右侧安全换道
        test_lane_change(agent_id=10, direction=1, force=0)
    
    if args.listen:
        listen_for_responses()

if __name__ == "__main__":
    main() 