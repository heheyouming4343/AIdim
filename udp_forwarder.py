#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UDP端口转发工具
从一个UDP端口接收数据，然后转发到另一个端口
"""

import socket
import binascii
import time
import sys
import threading

# 默认配置
SOURCE_PORT = 20000  # Resim发送消息的端口
TARGET_PORT = 25000  # 转发目标端口
TARGET_IP = "127.0.0.1"  # 转发目标IP

def udp_forwarder(source_port, target_ip, target_port):
    """
    UDP数据转发函数
    
    参数:
        source_port: 源端口 (接收数据的端口)
        target_ip: 目标IP (转发到哪个IP)
        target_port: 目标端口 (转发到哪个端口)
    """
    # 创建接收socket
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # 创建发送socket
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # 绑定到源端口
    try:
        recv_sock.bind(("0.0.0.0", source_port))
        print(f"成功绑定到源端口 {source_port}")
        print(f"准备转发到 {target_ip}:{target_port}")
    except OSError as e:
        print(f"错误: 无法绑定到源端口 {source_port} - {e}")
        print("请确认该端口没有被其他程序占用")
        return
    
    # 设置超时，便于退出
    recv_sock.settimeout(1)
    
    # 转发计数
    forward_count = 0
    
    try:
        while True:
            try:
                # 接收数据
                data, addr = recv_sock.recvfrom(8192)
                
                # 打印接收信息
                print(f"\n接收到来自 {addr[0]}:{addr[1]} 的数据 ({len(data)} 字节)")
                
                # 尝试解析为ASCII
                try:
                    ascii_data = data.decode('utf-8', errors='replace')
                    print(f"内容: {ascii_data}")
                except:
                    hex_data = binascii.hexlify(data).decode()
                    print(f"内容: (二进制) {hex_data[:60]}...")
                
                # 转发数据
                send_sock.sendto(data, (target_ip, target_port))
                forward_count += 1
                print(f"已转发到 {target_ip}:{target_port} (总计: {forward_count})")
                
            except socket.timeout:
                # 超时，打印点表示程序还在运行
                sys.stdout.write(".")
                sys.stdout.flush()
            except Exception as e:
                print(f"处理数据时出错: {e}")
    finally:
        recv_sock.close()
        send_sock.close()
        print("\n转发器已关闭")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="UDP端口转发工具")
    parser.add_argument("--source", type=int, default=SOURCE_PORT, 
                        help=f"源端口 (默认: {SOURCE_PORT})")
    parser.add_argument("--target-port", type=int, default=TARGET_PORT, 
                        help=f"目标端口 (默认: {TARGET_PORT})")
    parser.add_argument("--target-ip", type=str, default=TARGET_IP, 
                        help=f"目标IP (默认: {TARGET_IP})")
    args = parser.parse_args()
    
    print("===== UDP端口转发工具 =====")
    print(f"监听源端口: {args.source}")
    print(f"转发目标: {args.target_ip}:{args.target_port}")
    print("按Ctrl+C退出")
    print("-" * 30)
    
    try:
        udp_forwarder(args.source, args.target_ip, args.target_port)
    except KeyboardInterrupt:
        print("\n用户中断，退出中...")

if __name__ == "__main__":
    main() 