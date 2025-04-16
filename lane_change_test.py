#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Resim 车道变更命令发送工具
严格按照Resim代码中实现的格式发送命令
"""

import socket
import struct
import time
import binascii
import logging
import argparse

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ResimLaneChangeTester")

# Resim UDP配置 - 必须与Resim期望的端口匹配
RESIM_IP = "127.0.0.1"
RESIM_PORT = 20001  # Resim接收命令的端口
RECEIVE_PORT = 20000  # 接收Resim响应的端口

def send_command(data, ip=RESIM_IP, port=RESIM_PORT):
    """发送命令到Resim并返回是否成功"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(data, (ip, port))
        sock.close()
        
        # 打印发送的数据
        hex_data = binascii.hexlify(data).decode()
        logger.info(f"已发送命令到 {ip}:{port}: {hex_data}")
        return True
    except Exception as e:
        logger.error(f"发送命令失败: {e}")
        return False

def create_lane_change_command(agent_id, direction, mode):
    """
    创建标准车道变更命令 - 严格按照Resim代码实现
    
    参数:
        agent_id (int): 车辆ID (0-99)
        direction (int): 变道方向 (0=左, 1=右)
        mode (int): 变道模式 (0=检查风险, 1=强制变道)
    
    返回:
        bytes: 二进制命令数据
    """
    # 使用Resim中期望的格式: 'C' + 'L' + agent_id + direction + mode
    # 从Reisim/udpthread.cpp中可以看到正确的格式
    return b'CL' + struct.pack('<iii', agent_id, direction, mode)

def create_assigned_lane_change_command(agent_id, direction, mode, distance):
    """
    创建指定距离车道变更命令
    
    参数:
        agent_id (int): 车辆ID (0-99)
        direction (int): 变道方向 (0=左, 1=右)
        mode (int): 变道模式 (0=检查风险, 1=强制变道)
        distance (float): 变道距离 (米)
    
    返回:
        bytes: 二进制命令数据
    """
    # 使用Resim中期望的格式: 'C' + 'A' + 'L' + agent_id + direction + mode + distance
    return b'CAL' + struct.pack('<iiif', agent_id, direction, mode, distance)

def create_start_simulation_command():
    """创建开始模拟命令"""
    return b'CS'

def create_stop_simulation_command():
    """创建停止模拟命令"""
    return b'CP'

def create_test_message():
    """创建测试消息"""
    return b'TEST_MESSAGE_FROM_PYTHON'

def listen_for_response(timeout=5, receive_port=RECEIVE_PORT):
    """
    监听来自Resim的UDP响应
    
    参数:
        timeout (int): 等待响应的超时时间(秒)
        receive_port (int): 用于接收响应的端口
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.1)  # 设置短超时以便快速检测端口是否可用
        
        try:
            # 尝试绑定端口
            sock.bind(("0.0.0.0", receive_port))
            logger.info(f"监听来自Resim的响应，端口: {receive_port}，超时: {timeout}秒")
        except OSError as e:
            if e.errno == 10048:  # 端口已被占用
                logger.warning(f"端口 {receive_port} 已被占用，跳过响应监听")
                return
            else:
                raise
                
        sock.settimeout(timeout)  # 重置为正常超时
        
        # 监听数据
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                data, addr = sock.recvfrom(8192)
                hex_data = binascii.hexlify(data).decode()
                logger.info(f"收到来自 {addr[0]}:{addr[1]} 的响应: {hex_data}")
                
                # 尝试解析响应
                if data.startswith(b'RL'):
                    # 车道变更响应
                    try:
                        agent_id, result, reason = struct.unpack('<iii', data[2:14])
                        result_str = "成功" if result == 1 else "失败"
                        reason_codes = {
                            0: "无原因",
                            1: "车道不存在",
                            2: "危险状况",
                            3: "无法变道"
                        }
                        reason_str = reason_codes.get(reason, f"未知原因({reason})")
                        logger.info(f"车道变更响应: 车辆ID={agent_id}, 结果={result_str}, 原因={reason_str}")
                    except Exception as e:
                        logger.error(f"解析响应出错: {e}")
                else:
                    logger.info(f"收到未知响应，前缀: {data[:4]}")
            except socket.timeout:
                # 短超时，继续循环
                continue
                
    except socket.timeout:
        logger.warning("等待响应超时")
    except Exception as e:
        logger.error(f"接收响应出错: {e}")
    finally:
        try:
            sock.close()
        except:
            pass

def run_lane_change_test(agent_id=10, direction=0, mode=1, distance=None, receive_port=RECEIVE_PORT):
    """
    运行车道变更测试
    
    参数:
        agent_id (int): 车辆ID
        direction (int): 变道方向 (0=左, 1=右)
        mode (int): 变道模式 (0=检查风险, 1=强制变道)
        distance (float): 变道距离 (如果指定)
        receive_port (int): 接收响应的端口
    """
    direction_str = "左" if direction == 0 else "右"
    mode_str = "检查风险" if mode == 0 else "强制变道"
    
    if distance is not None:
        logger.info(f"发送指定距离变道命令: 车辆ID={agent_id}, 方向={direction_str}, 模式={mode_str}, 距离={distance}米")
        command = create_assigned_lane_change_command(agent_id, direction, mode, distance)
    else:
        logger.info(f"发送标准变道命令: 车辆ID={agent_id}, 方向={direction_str}, 模式={mode_str}")
        command = create_lane_change_command(agent_id, direction, mode)
    
    if send_command(command):
        # 等待并监听响应
        listen_for_response(timeout=3, receive_port=receive_port)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Resim车道变更测试工具")
    parser.add_argument('--agent', type=int, default=10, help="车辆ID (默认: 10)")
    parser.add_argument('--direction', type=int, choices=[0, 1], default=0, help="变道方向 (0=左, 1=右) (默认: 0)")
    parser.add_argument('--mode', type=int, choices=[0, 1], default=1, help="变道模式 (0=检查风险, 1=强制变道) (默认: 1)")
    parser.add_argument('--distance', type=float, help="变道距离 (米) (可选)")
    parser.add_argument('--count', type=int, default=1, help="发送次数 (默认: 1)")
    parser.add_argument('--interval', type=float, default=2.0, help="发送间隔 (秒) (默认: 2.0)")
    parser.add_argument('--start', action='store_true', help="先发送开始模拟命令")
    parser.add_argument('--ip', type=str, default=RESIM_IP, help=f"Resim IP地址 (默认: {RESIM_IP})")
    parser.add_argument('--port', type=int, default=RESIM_PORT, help=f"Resim命令接收端口 (默认: {RESIM_PORT})")
    parser.add_argument('--receive-port', type=int, default=RECEIVE_PORT, help=f"接收Resim响应的端口 (默认: {RECEIVE_PORT})")
    parser.add_argument('--no-listen', action='store_true', help="不监听响应")
    
    args = parser.parse_args()
    
    logger.info("===== Resim车道变更测试工具 =====")
    logger.info(f"Resim地址: {args.ip}:{args.port}")
    logger.info(f"接收响应端口: {args.receive_port}")
    
    # 如果请求，先发送开始模拟命令
    if args.start:
        logger.info("发送开始模拟命令 (CS)")
        send_command(create_start_simulation_command(), args.ip, args.port)
        time.sleep(1)
    
    # 发送测试消息
    logger.info("发送测试消息")
    send_command(create_test_message(), args.ip, args.port)
    time.sleep(1)
    
    # 发送多次变道命令
    for i in range(args.count):
        if args.count > 1:
            logger.info(f"发送第 {i+1}/{args.count} 次变道命令")
        
        if args.no_listen:
            # 只发送命令，不监听响应
            direction_str = "左" if args.direction == 0 else "右"
            mode_str = "检查风险" if args.mode == 0 else "强制变道"
            
            if args.distance is not None:
                logger.info(f"发送指定距离变道命令: 车辆ID={args.agent}, 方向={direction_str}, 模式={mode_str}, 距离={args.distance}米")
                command = create_assigned_lane_change_command(args.agent, args.direction, args.mode, args.distance)
            else:
                logger.info(f"发送标准变道命令: 车辆ID={args.agent}, 方向={direction_str}, 模式={mode_str}")
                command = create_lane_change_command(args.agent, args.direction, args.mode)
                
            send_command(command, args.ip, args.port)
        else:
            # 发送命令并监听响应
            run_lane_change_test(args.agent, args.direction, args.mode, args.distance, args.receive_port)
        
        if i < args.count - 1:
            logger.info(f"等待 {args.interval} 秒...")
            time.sleep(args.interval)
    
    logger.info("测试完成")

if __name__ == "__main__":
    main() 