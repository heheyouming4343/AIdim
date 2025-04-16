#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
极简UDP监听工具
仅用于测试Resim发送的UDP消息
"""

import socket
import binascii
import time
import sys
import argparse

def start_listener(port=20000):
    # 创建UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # 绑定到指定端口
    try:
        sock.bind(("0.0.0.0", port))
        print(f"成功绑定到端口 {port}，等待接收Resim消息...")
    except OSError as e:
        print(f"错误: 无法绑定到端口 {port} - {e}")
        print("请确认该端口没有被其他程序占用")
        return
    
    # 设置超时，以便可以通过Ctrl+C退出
    sock.settimeout(1)
    
    try:
        while True:
            try:
                # 接收数据
                data, addr = sock.recvfrom(8192)
                
                # 以ASCII和十六进制格式显示数据
                print("\n" + "-"*60)
                print(f"收到来自 {addr[0]}:{addr[1]} 的数据 ({len(data)} 字节)")
                
                # 尝试解析为ASCII
                try:
                    ascii_data = data.decode('utf-8', errors='replace')
                    print(f"ASCII: {ascii_data}")
                except:
                    print("无法解析为ASCII")
                
                # 显示十六进制
                hex_data = binascii.hexlify(data).decode()
                print(f"HEX: {hex_data}")
                print("-"*60)
            
            except socket.timeout:
                # 超时，打印点表示程序还在运行
                sys.stdout.write(".")
                sys.stdout.flush()
                continue
            except KeyboardInterrupt:
                break
    finally:
        sock.close()
        print("\n监听器已关闭")

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="极简UDP监听工具")
    parser.add_argument("--port", type=int, default=20000, help="监听端口 (默认: 25000)")
    args = parser.parse_args()
    
    print("极简UDP监听工具")
    print(f"监听端口: {args.port}")
    print("按Ctrl+C退出")
    
    try:
        start_listener(args.port)
    except KeyboardInterrupt:
        print("\n用户中断，退出中...") 