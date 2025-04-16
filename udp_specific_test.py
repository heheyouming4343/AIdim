#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Resim UDP 车道变更命令发送工具
精确匹配Resim期望的CL命令格式
"""

import socket
import struct
import time
import binascii
import logging
import sys
import argparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ResimLaneChangeSender")

# UDP配置 - Resim默认接收端口
RESIM_IP = "127.0.0.1"
RESIM_PORT = 20001  # Resim接收命令的端口

def send_lane_change_command(agent_id, direction, mode, count=1, interval=1.0, ip=None, port=None):
    """发送车道变更命令到Resim
    
    参数:
        agent_id (int): 车辆ID
        direction (int): 方向 (0=左, 1=右)
        mode (int): 模式 (0=检查风险, 1=强制变道)
        count (int): 重复发送次数
        interval (float): 发送间隔(秒)
        ip (str): 目标IP地址
        port (int): 目标端口
    """
    if ip is None:
        ip = RESIM_IP
    if port is None:
        port = RESIM_PORT
        
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        # 创建严格按照Resim UDPThread代码中要求的CL命令
        # CL + struct.pack('<iii', agent_id, direction, mode)
        command_data = b'CL' + struct.pack('<iii', agent_id, direction, mode)
        
        # 打印命令详情
        hex_data = binascii.hexlify(command_data).decode()
        direction_str = "左" if direction == 0 else "右"
        mode_str = "检查风险" if mode == 0 else "强制"
        
        logger.info(f"发送车道变更命令:")
        logger.info(f"  车辆ID: {agent_id}")
        logger.info(f"  方向: {direction_str} ({direction})")
        logger.info(f"  模式: {mode_str} ({mode})")
        logger.info(f"  原始数据: {hex_data}")
        logger.info(f"  目标: {ip}:{port}")
        logger.info(f"  发送次数: {count}, 间隔: {interval}秒")
        logger.info("-" * 40)
        
        # 发送指定次数
        for i in range(count):
            if i > 0:
                time.sleep(interval)
                
            # 发送数据
            sock.sendto(command_data, (ip, port))
            logger.info(f"[{i+1}/{count}] 已发送命令: {hex_data}")
            
        logger.info(f"完成发送 {count} 次命令")
        
    except Exception as e:
        logger.error(f"发送命令时出错: {e}")
    finally:
        sock.close()

def send_start_simulation_command(ip=None, port=None):
    """发送开始模拟命令到Resim"""
    if ip is None:
        ip = RESIM_IP
    if port is None:
        port = RESIM_PORT
        
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        # 创建CS命令 (开始模拟)
        command_data = b'CS'
        
        # 打印命令详情
        hex_data = binascii.hexlify(command_data).decode()
        logger.info(f"发送开始模拟命令 (CS): {hex_data}")
        
        # 发送数据
        sock.sendto(command_data, (ip, port))
        logger.info(f"已发送开始模拟命令")
        
    except Exception as e:
        logger.error(f"发送命令时出错: {e}")
    finally:
        sock.close()

def send_test_pattern(ip=None, port=None):
    """发送一系列不同格式的命令测试哪种被接受"""
    if ip is None:
        ip = RESIM_IP
    if port is None:
        port = RESIM_PORT
        
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        # 测试参数
        agent_id = 10
        direction = 0  # 0=左, 1=右
        mode = 1       # 0=检查风险, 1=强制变道
        
        # 不同格式的命令
        test_commands = [
            # 原格式 'CL' + 参数 (从UDPThread.cpp的代码分析)
            (b'CL' + struct.pack('<iii', agent_id, direction, mode), 
             "格式1: 'CL' + 参数 (原格式)"),
            
            # 尝试其他可能的前缀
            (b'FCL' + struct.pack('<iii', agent_id, direction, mode),
             "格式2: 'FCL' + 参数"),
            
            # 使用不同的参数排列
            (b'CL' + struct.pack('<iii', agent_id, mode, direction),
             "格式3: 'CL' + 参数顺序变化"), 
            
            # 使用大端字节序
            (b'CL' + struct.pack('>iii', agent_id, direction, mode),
             "格式4: 'CL' + 参数 (大端字节序)"),
             
            # 添加额外参数
            (b'CL' + struct.pack('<iiif', agent_id, direction, mode, 100.0),
             "格式5: 'CL' + 参数 + 额外float"),
             
            # 尝试替代格式
            (b'ACL' + struct.pack('<iii', agent_id, direction, mode),
             "格式6: 'ACL' + 参数"),
             
            # 尝试命令中间有分隔符
            (b'CL|' + struct.pack('<iii', agent_id, direction, mode),
             "格式7: 'CL|' + 参数"),
        ]
        
        logger.info(f"开始发送测试命令序列到 {ip}:{port}")
        logger.info("-" * 40)
        
        # 首先发送启动模拟命令
        sock.sendto(b'CS', (ip, port))
        logger.info("已发送开始模拟命令 (CS)")
        time.sleep(2)
        
        # 逐一发送测试命令
        for i, (command, description) in enumerate(test_commands):
            # 打印命令详情
            hex_data = binascii.hexlify(command).decode()
            logger.info(f"[{i+1}/{len(test_commands)}] 发送 {description}")
            logger.info(f"  原始数据: {hex_data}")
            
            # 发送数据
            sock.sendto(command, (ip, port))
            
            # 暂停一会等待处理
            time.sleep(2)
            
        logger.info(f"测试序列发送完成")
        
    except Exception as e:
        logger.error(f"发送测试命令时出错: {e}")
    finally:
        sock.close()

def main():
    # 定义命令行参数解析器
    parser = argparse.ArgumentParser(description='Resim UDP 车道变更命令发送工具')
    
    # 定义子命令
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # 车道变更命令
    lane_parser = subparsers.add_parser('lane', help='发送车道变更命令')
    lane_parser.add_argument('--id', type=int, default=10, help='车辆ID (默认: 10)')
    lane_parser.add_argument('--dir', type=int, choices=[0, 1], default=0, 
                           help='方向: 0=左, 1=右 (默认: 0)')
    lane_parser.add_argument('--mode', type=int, choices=[0, 1], default=1, 
                           help='模式: 0=检查风险, 1=强制变道 (默认: 1)')
    lane_parser.add_argument('--count', type=int, default=1, 
                           help='重复发送次数 (默认: 1)')
    lane_parser.add_argument('--interval', type=float, default=1.0, 
                           help='发送间隔(秒) (默认: 1.0)')
    
    # 开始模拟命令
    start_parser = subparsers.add_parser('start', help='发送开始模拟命令')
    
    # 测试模式
    test_parser = subparsers.add_parser('test', help='发送测试命令序列')
    
    # IP和端口参数
    parser.add_argument('--ip', type=str, default=RESIM_IP,
                      help=f'Resim IP地址 (默认: {RESIM_IP})')
    parser.add_argument('--port', type=int, default=RESIM_PORT,
                      help=f'Resim端口 (默认: {RESIM_PORT})')
    
    args = parser.parse_args()
    
    # 执行相应的命令
    if args.command == 'lane':
        send_lane_change_command(args.id, args.dir, args.mode, args.count, args.interval, args.ip, args.port)
    elif args.command == 'start':
        send_start_simulation_command(args.ip, args.port)
    elif args.command == 'test':
        send_test_pattern(args.ip, args.port)
    else:
        # 如果没有指定命令，显示帮助
        parser.print_help()

if __name__ == "__main__":
    main() 