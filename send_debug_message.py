#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UDP调试消息发送工具
用于测试Resim的UDP通信功能
"""

import socket
import struct
import time
import binascii
import sys

# 配置UDP目标
TARGET_IP = "127.0.0.1"  # 本地地址
TARGET_PORT = 20000      # udp_receiver.py默认监听的端口

def send_test_message():
    """发送测试消息到接收端"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        # 创建测试消息
        test_message = b'TEST_MESSAGE_FROM_PYTHON'
        
        # 发送消息
        sock.sendto(test_message, (TARGET_IP, TARGET_PORT))
        print(f"已发送消息: {test_message.decode()} 到 {TARGET_IP}:{TARGET_PORT}")
        
        # 等待1秒
        time.sleep(1)
        
        # 发送带计数器的测试消息
        counter = 1
        counter_message = b'TSPY' + struct.pack('<i', counter) + b'Hello from debug sender'
        
        sock.sendto(counter_message, (TARGET_IP, TARGET_PORT))
        print(f"已发送带计数器消息 #{counter} 到 {TARGET_IP}:{TARGET_PORT}")
        
        # 等待1秒
        time.sleep(1)
        
        # 发送模拟Resim消息
        resim_message = b'RSd' + b'Agent data simulation'
        
        sock.sendto(resim_message, (TARGET_IP, TARGET_PORT))
        print(f"已发送模拟Resim消息 'RSd' 到 {TARGET_IP}:{TARGET_PORT}")
        
        print("测试消息发送完成")
        
    except Exception as e:
        print(f"发送消息出错: {e}")
    finally:
        sock.close()

def send_continuous_messages(count=10, interval=1.0):
    """持续发送测试消息
    
    参数:
        count (int): 发送消息的次数
        interval (float): 发送间隔，单位秒
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        print(f"开始持续发送消息: 次数={count}, 间隔={interval}秒")
        
        for i in range(count):
            # 创建带计数的消息
            counter = i + 1
            message = b'TSPY' + struct.pack('<i', counter) + f"Continuous test message #{counter}".encode()
            
            # 发送消息
            sock.sendto(message, (TARGET_IP, TARGET_PORT))
            print(f"[{counter}/{count}] 已发送测试消息")
            
            # 等待指定间隔
            if i < count - 1:  # 最后一次不需要等待
                time.sleep(interval)
        
        print("持续发送消息完成")
        
    except KeyboardInterrupt:
        print("\n用户中断，停止发送")
    except Exception as e:
        print(f"发送消息出错: {e}")
    finally:
        sock.close()

def main():
    """主函数"""
    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == 'continuous':
            # 获取可选参数
            count = 10
            interval = 1.0
            
            if len(sys.argv) > 2:
                try:
                    count = int(sys.argv[2])
                except ValueError:
                    print(f"无效的消息数量: {sys.argv[2]}，使用默认值: 10")
            
            if len(sys.argv) > 3:
                try:
                    interval = float(sys.argv[3])
                except ValueError:
                    print(f"无效的时间间隔: {sys.argv[3]}，使用默认值: 1.0")
            
            send_continuous_messages(count, interval)
        else:
            print(f"未知命令: {sys.argv[1]}")
            print("可用命令:")
            print("  continuous [次数] [间隔]: 持续发送测试消息")
            print("  (无参数): 发送单次测试消息")
    else:
        send_test_message()

if __name__ == "__main__":
    main() 