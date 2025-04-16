#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Resim模拟器
模拟Resim接收UDP命令并返回响应
"""

import socket
import struct
import time
import binascii
import sys
import threading

# 默认配置
LISTEN_PORT = 20001  # Resim命令接收端口
SEND_PORT = 20000    # Resim发送响应的端口
LOCAL_IP = "0.0.0.0" # 监听IP
TARGET_IP = "127.0.0.1" # 发送响应的目标IP

def handle_command(data, addr, send_sock):
    """处理接收到的命令并返回响应"""
    # 命令处理逻辑
    hex_data = binascii.hexlify(data).decode()
    
    print(f"\n接收到命令: {hex_data}")
    
    if len(data) < 2:
        print("命令太短，无法处理")
        return
    
    # 尝试解析命令前缀
    try:
        prefix = data[:2].decode('ascii', errors='replace')
    except:
        prefix = hex_data[:4]
    
    # 根据不同命令返回不同的响应
    response = None
    
    if prefix == 'CS':
        print("收到开始模拟命令")
        # 返回模拟状态为"运行中"
        response = b'SS' + struct.pack('<i', 1)
        
    elif prefix == 'CP':
        print("收到暂停模拟命令")
        # 返回模拟状态为"已暂停"
        response = b'SS' + struct.pack('<i', 2)
    
    elif prefix == 'CL' and len(data) >= 14:
        try:
            agent_id = struct.unpack('<i', data[2:6])[0]
            direction = struct.unpack('<i', data[6:10])[0]
            mode = struct.unpack('<i', data[10:14])[0]
            
            direction_str = "左" if direction == 0 else "右"
            mode_str = "检查风险" if mode == 0 else "强制变道"
            
            print(f"收到车道变更命令: 车辆ID={agent_id}, 方向={direction_str}, 模式={mode_str}")
            
            # 返回车道变更成功响应
            # RL + agent_id + result(1=成功) + reason(0=无原因)
            response = b'RL' + struct.pack('<iii', agent_id, 1, 0)
            
        except Exception as e:
            print(f"解析CL命令出错: {e}")
    
    # 测试消息
    elif data.startswith(b'TEST_'):
        try:
            message = data.decode('utf-8', errors='replace')
            print(f"收到测试消息: {message}")
            # 返回测试响应
            response = b'TEST_RESPONSE_FROM_RESIM'
        except:
            print("解析测试消息失败")
    
    # 发送响应
    if response:
        print(f"发送响应: {binascii.hexlify(response).decode()}")
        
        try:
            send_sock.sendto(response, (TARGET_IP, SEND_PORT))
            print(f"已发送响应到 {TARGET_IP}:{SEND_PORT}")
        except Exception as e:
            print(f"发送响应失败: {e}")
    else:
        print(f"未处理命令: {prefix}")

def resim_simulator(listen_port, target_ip, send_port):
    """
    模拟Resim的UDP通信
    
    参数:
        listen_port: 监听端口 (接收命令)
        target_ip: 发送响应的目标IP
        send_port: 发送响应的目标端口
    """
    global TARGET_IP
    TARGET_IP = target_ip
    
    # 创建接收socket
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # 创建发送socket
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # 绑定到监听端口
    try:
        recv_sock.bind((LOCAL_IP, listen_port))
        print(f"成功绑定到端口 {listen_port}")
        print(f"将发送响应到 {target_ip}:{send_port}")
    except OSError as e:
        print(f"错误: 无法绑定到端口 {listen_port} - {e}")
        print("请确认该端口没有被其他程序占用")
        return
    
    # 设置超时，便于退出
    recv_sock.settimeout(1)
    
    # 命令计数
    command_count = 0
    
    # 发送启动消息
    startup_msg = b'TEST_MESSAGE_FROM_RESIM'
    try:
        send_sock.sendto(startup_msg, (target_ip, send_port))
        print(f"已发送启动消息到 {target_ip}:{send_port}")
    except Exception as e:
        print(f"发送启动消息失败: {e}")
    
    try:
        while True:
            try:
                # 接收数据
                data, addr = recv_sock.recvfrom(8192)
                
                command_count += 1
                print(f"\n接收到来自 {addr[0]}:{addr[1]} 的命令 #{command_count} ({len(data)} 字节)")
                
                # 处理命令并发送响应
                handle_command(data, addr, send_sock)
                
            except socket.timeout:
                # 超时，打印点表示程序还在运行
                sys.stdout.write(".")
                sys.stdout.flush()
            except Exception as e:
                print(f"处理数据时出错: {e}")
    finally:
        recv_sock.close()
        send_sock.close()
        print("\n模拟器已关闭")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Resim模拟器")
    parser.add_argument("--listen-port", type=int, default=LISTEN_PORT, 
                        help=f"监听端口 (默认: {LISTEN_PORT})")
    parser.add_argument("--send-port", type=int, default=SEND_PORT, 
                        help=f"发送响应的端口 (默认: {SEND_PORT})")
    parser.add_argument("--target-ip", type=str, default=TARGET_IP, 
                        help=f"发送响应的目标IP (默认: {TARGET_IP})")
    args = parser.parse_args()
    
    print("===== Resim模拟器 =====")
    print(f"监听端口: {args.listen_port}")
    print(f"响应目标: {args.target_ip}:{args.send_port}")
    print("按Ctrl+C退出")
    print("-" * 30)
    
    try:
        resim_simulator(args.listen_port, args.target_ip, args.send_port)
    except KeyboardInterrupt:
        print("\n用户中断，退出中...")

if __name__ == "__main__":
    main() 