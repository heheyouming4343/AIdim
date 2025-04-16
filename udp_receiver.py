#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Resim UDP 接收解析工具
用于监听和解析来自Resim的UDP消息
"""

import socket
import struct
import time
import binascii
import logging
import sys
import threading
import argparse
import os
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ResimUDPReceiver")

# UDP配置 - 用于接收Resim消息的端口
DEFAULT_IP = "0.0.0.0"    # 监听所有接口
DEFAULT_PORTS = [20000, 20001]  # 默认监听两个端口(Resim状态更新和命令端口)

# 全局统计信息
stats = {
    'total_packets': 0,
    'last_packet_time': None,
    'command_counts': {},    # 按命令类型统计
    'last_commands': []      # 最近接收的命令
}

# 定义一个标志，用于控制线程
running = True

def parse_resim_data(data):
    """解析Resim发送的各种数据格式"""
    try:
        # 获取数据包的十六进制表示，用于调试
        hex_data = binascii.hexlify(data).decode()
        
        # 解析数据前缀
        if not data or len(data) < 2:
            return f"数据包太短: {hex_data}"
        
        try:
            # 尝试解析前2-4个字符作为ASCII
            prefix2 = data[:2].decode('ascii', errors='replace')
            prefix3 = data[:3].decode('ascii', errors='replace') if len(data) >= 3 else prefix2
            prefix4 = data[:4].decode('ascii', errors='replace') if len(data) >= 4 else prefix3
        except:
            prefix2 = hex_data[:4]
            prefix3 = hex_data[:6]
            prefix4 = hex_data[:8]
        
        # 分析不同前缀的数据
        if prefix3 == 'RSd':
            # 这是发送到SCore的同步信号或车辆状态数据包
            if len(data) == 3:
                return f"同步信号(SCore): {prefix3}"
            return f"车辆状态数据: 前缀={prefix3}, 大小={len(data)}字节"
        
        # 测试消息
        if data.startswith(b'TEST_'):
            try:
                message = data.decode('utf-8', errors='replace')
                return f"Resim测试字符串: {message}"
            except:
                return f"Resim测试数据: {hex_data}"
                
        # Resim可能发送的各种命令前缀
        
        # 代理位置/状态数据    
        if prefix2 == 'AP':
            # Agent Position数据
            return f"代理位置数据: 大小={len(data)}字节"
            
        elif prefix2 == 'AS':
            # Agent State数据
            return f"代理状态数据: 大小={len(data)}字节"
        
        # 交通信号灯数据
        elif prefix2 == 'TS':
            return f"交通信号灯数据: 大小={len(data)}字节"
        
        # 测试数据
        elif data.startswith(b'TSPY'):
            try:
                counter = struct.unpack('<i', data[4:8])[0]
                message = data[8:].decode('utf-8', errors='replace')
                return f"Resim测试消息 #{counter}: {message}"
            except:
                return f"Resim测试消息: {data[4:].decode('utf-8', errors='replace')}"
                
        # 模拟状态信号
        elif prefix2 == 'SS':
            if len(data) >= 6:
                try:
                    status = struct.unpack('<i', data[2:6])[0]
                    status_str = {
                        0: "已停止",
                        1: "正在运行",
                        2: "已暂停"
                    }.get(status, f"未知状态({status})")
                    return f"模拟状态: {status_str}"
                except:
                    return f"模拟状态数据: 无法解析, 数据={hex_data}"
            return f"模拟状态数据: 大小={len(data)}字节"
                
        # 车道变更命令
        elif prefix2 == 'CL' and len(data) >= 14:
            try:
                agent_id = struct.unpack('<i', data[2:6])[0]
                direction = struct.unpack('<i', data[6:10])[0]
                mode = struct.unpack('<i', data[10:14])[0]
                return f"车道变更命令: 车辆ID={agent_id}, 方向={'左' if direction==0 else '右'}, 模式={'检查风险' if mode==0 else '强制变更'}"
            except Exception as e:
                return f"CL命令解析出错: {e}, 数据={hex_data}"
                
        # 车道变更响应
        elif prefix2 == 'RL' and len(data) >= 14:
            try:
                agent_id = struct.unpack('<i', data[2:6])[0]
                result = struct.unpack('<i', data[6:10])[0]
                reason = struct.unpack('<i', data[10:14])[0]
                return f"车道变更响应: 车辆ID={agent_id}, 结果={'成功' if result==1 else '失败'}, 原因代码={reason}"
            except Exception as e:
                return f"RL命令解析出错: {e}, 数据={hex_data}"
                
        # 开始模拟命令
        elif prefix2 == 'CS':
            return "开始模拟命令"
            
        # 暂停模拟命令
        elif prefix2 == 'CP':
            return "暂停模拟命令"
            
        # 继续模拟命令
        elif prefix2 == 'CR':
            return "继续模拟命令"
        
        # 其他常见前缀
        elif prefix2 in ['RS', 'RP', 'RQ', 'CC']:
            return f"Resim命令: 前缀={prefix2}, 数据={hex_data}"
        
        # 如果无法识别，返回通用信息
        return f"未识别的Resim数据: 前缀={prefix4}, 大小={len(data)}字节, 数据={hex_data[:60]}..."
        
    except Exception as e:
        logger.error(f"解析Resim数据出错: {e}")
        return f"解析错误: {str(e)}, 数据={hex_data[:60] if 'hex_data' in locals() else '未知'}"

def udp_listener(ip, port, log_file):
    """监听特定端口的UDP消息的线程函数"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((ip, port))
        sock.settimeout(0.5)  # 设置超时以便定期检查状态
        
        logger.info(f"开始在 {ip}:{port} 监听UDP消息...")
        
        global running
        while running:
            try:
                # 尝试接收数据
                data, addr = sock.recvfrom(8192)  # 增大缓冲区以接收更大的数据包
                
                # 更新统计信息
                stats['total_packets'] += 1
                stats['last_packet_time'] = datetime.now()
                
                # 解析数据
                info = parse_resim_data(data)
                
                # 记录命令
                stats['last_commands'].append({
                    'time': stats['last_packet_time'],
                    'port': port,
                    'from': addr,
                    'data': binascii.hexlify(data).decode(),
                    'info': info
                })
                
                # 限制最近命令列表大小
                if len(stats['last_commands']) > 100:
                    stats['last_commands'] = stats['last_commands'][-100:]
                
                # 更新命令类型统计
                if len(data) >= 2:
                    try:
                        cmd_type = data[:2].decode('ascii', errors='replace')
                    except:
                        cmd_type = binascii.hexlify(data[:2]).decode()
                    
                    stats['command_counts'][cmd_type] = stats['command_counts'].get(cmd_type, 0) + 1
                
                # 记录到控制台
                logger.info(f"[端口 {port}] 收到来自 {addr[0]}:{addr[1]} 的数据: {info}")
                
                # 详细记录到文件
                with open(log_file, 'a', encoding='utf-8') as f:
                    hex_data = binascii.hexlify(data).decode()
                    try:
                        prefix = data[:4].decode('ascii', errors='replace') if len(data) >= 4 else ""
                    except:
                        prefix = hex_data[:8]
                    
                    f.write(f"[{datetime.now()}] [端口 {port}] [{addr[0]}:{addr[1]}] [{len(data)}字节] [{prefix}] {hex_data}\n")
                    f.write(f"解析: {info}\n\n")
                
            except socket.timeout:
                # 超时，继续循环
                pass
            except Exception as e:
                logger.error(f"[端口 {port}] 接收或处理数据时出错: {e}")
                time.sleep(1)  # 避免错误情况下过快循环
        
        sock.close()
        logger.info(f"[端口 {port}] UDP监听器已关闭")
            
    except socket.error as e:
        if e.errno == 10048:
            logger.error(f"端口 {port} 已被占用，无法监听")
        else:
            logger.error(f"[端口 {port}] 创建套接字时出错: {e}")
    except Exception as e:
        logger.error(f"[端口 {port}] 初始化监听器时出错: {e}")

def display_status():
    """显示统计信息的线程函数"""
    last_total = 0
    
    global running
    while running:
        try:
            time.sleep(5)  # 每5秒显示一次状态
            
            # 计算这一时间段接收的数据包数量
            current_total = stats['total_packets']
            packets_per_period = current_total - last_total
            last_total = current_total
            
            # 检查最后一个数据包的时间
            last_time = stats['last_packet_time']
            time_since_last = (datetime.now() - last_time).total_seconds() if last_time else float('inf')
            
            # 显示状态信息
            logger.info("-" * 50)
            logger.info(f"状态更新: 总共接收 {current_total} 个数据包")
            logger.info(f"过去5秒接收: {packets_per_period} 个数据包 ({packets_per_period/5:.1f}包/秒)")
            
            # 显示最后接收时间
            if last_time:
                if time_since_last < 60:
                    logger.info(f"最后接收时间: {last_time.strftime('%H:%M:%S')} ({time_since_last:.1f}秒前)")
                else:
                    logger.warning(f"最后接收时间: {last_time.strftime('%H:%M:%S')} ({time_since_last:.1f}秒前) - 可能连接已断开")
            else:
                logger.warning("尚未接收到任何数据包")
                
            # 显示命令统计
            if stats['command_counts']:
                logger.info("命令类型统计:")
                for cmd, count in sorted(stats['command_counts'].items(), key=lambda x: x[1], reverse=True):
                    logger.info(f"  {cmd}: {count}个")
                
            # 显示最近的几条命令
            if stats['last_commands']:
                logger.info("最近接收的命令:")
                for i, cmd in enumerate(reversed(stats['last_commands'][-5:])):
                    cmd_time = cmd['time'].strftime('%H:%M:%S')
                    cmd_port = cmd['port']
                    cmd_from = f"{cmd['from'][0]}:{cmd['from'][1]}"
                    cmd_info = cmd['info']
                    logger.info(f"  {i+1}. [{cmd_time}] [端口 {cmd_port}] [{cmd_from}] {cmd_info}")
                    
            # 如果长时间没有接收到数据，显示警告
            if time_since_last > 30:
                logger.warning("警告: 长时间未收到数据包，请检查:")
                logger.warning("  1. Resim是否正在运行且已启动DS模式 (使用 --ds-mode 参数启动)")
                logger.warning("  2. 网络连接是否正常")
                logger.warning("  3. 是否启动了模拟 (发送 CS 命令)")
                logger.warning("  4. 防火墙是否阻止了UDP连接")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"显示状态时出错: {e}")

def main():
    # 首先定义命令行参数解析器
    parser = argparse.ArgumentParser(description='Resim UDP 接收解析工具')
    
    parser.add_argument('--ports', type=int, nargs='+', default=DEFAULT_PORTS,
                      help=f'监听端口列表 (默认: {" ".join(map(str, DEFAULT_PORTS))})')
    parser.add_argument('--ip', type=str, default=DEFAULT_IP,
                      help=f'监听IP地址 (默认: {DEFAULT_IP})')
    
    args = parser.parse_args()
    
    # 创建日志目录
    log_dir = "udp_logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"resim_udp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"开始记录Resim UDP数据: {datetime.now()}\n")
        f.write(f"监听端口: {args.ports}\n")
        f.write("格式: [时间戳] [端口] [来源IP:端口] [数据大小] [数据前缀] [完整十六进制数据]\n\n")
    
    try:
        logger.info("===== Resim UDP 接收解析工具 =====")
        logger.info(f"监听地址: {args.ip}, 端口: {args.ports}")
        logger.info(f"日志文件: {log_file}")
        logger.info("按Ctrl+C退出")
        logger.info("-" * 50)
        
        # 创建并启动监听线程
        listener_threads = []
        for port in args.ports:
            thread = threading.Thread(
                target=udp_listener, 
                args=(args.ip, port, log_file),
                daemon=True
            )
            thread.start()
            listener_threads.append(thread)
        
        # 创建并启动状态显示线程
        status_thread = threading.Thread(target=display_status, daemon=True)
        status_thread.start()
        
        # 等待用户中断
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("\n用户中断，正在关闭...")
                running = False
                break
    
    except Exception as e:
        logger.error(f"程序出错: {e}")
    
    # 等待线程结束
    running = False
    time.sleep(1)
    logger.info("程序已退出")

if __name__ == "__main__":
    main() 