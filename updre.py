#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import struct
import time
import datetime
import binascii
import sys
import threading
import os

# UDP监听配置
LISTEN_IP = ""  # 空字符串表示监听所有网卡
LISTEN_PORT = 20000  # Resim默认发送端口
BUFFER_SIZE = 4096  # 接收缓冲区大小

# 日志设置
LOG_FILE = "resim_udp_log.txt"
ENABLE_LOGGING = True  # 是否将接收数据保存到日志文件

class UDPReceiver:
    def __init__(self, ip="", port=20000, buffer_size=4096, enable_logging=True):
        self.ip = ip
        self.port = port
        self.buffer_size = buffer_size
        self.enable_logging = enable_logging
        self.socket = None
        self.running = False
        self.packet_count = 0
        self.last_packet_time = None
        self.log_file = LOG_FILE
        
        # 状态统计
        self.stats = {
            "total_packets": 0,
            "total_bytes": 0,
            "start_time": None,
            "command_types": {}
        }
    
    def setup(self):
        """设置UDP监听socket"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.ip, self.port))
            self.socket.settimeout(0.5)  # 设置超时，使循环可以定期检查退出条件
            print(f"UDP监听器已启动，正在监听 {self.ip if self.ip else '所有IP'}:{self.port}")
            return True
        except Exception as e:
            print(f"设置UDP监听器失败: {e}")
            return False
    
    def start(self):
        """启动UDP监听"""
        if not self.setup():
            return False
        
        self.running = True
        self.stats["start_time"] = datetime.datetime.now()
        
        # 创建状态显示线程
        status_thread = threading.Thread(target=self._status_display_thread)
        status_thread.daemon = True
        status_thread.start()
        
        try:
            print("开始监听UDP数据...")
            print("按Ctrl+C停止监听")
            print("=" * 60)
            
            while self.running:
                try:
                    # 接收数据
                    data, addr = self.socket.recvfrom(self.buffer_size)
                    
                    # 更新统计信息
                    self.stats["total_packets"] += 1
                    self.stats["total_bytes"] += len(data)
                    self.packet_count += 1
                    self.last_packet_time = datetime.datetime.now()
                    
                    # 处理接收到的数据
                    self._process_data(data, addr)
                    
                except socket.timeout:
                    # 超时继续循环
                    pass
        
        except KeyboardInterrupt:
            print("\n用户中断，停止监听")
        except Exception as e:
            print(f"\n监听出错: {e}")
        finally:
            self.stop()
            return True
    
    def stop(self):
        """停止UDP监听"""
        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None
        
        # 显示最终统计信息
        self._display_final_stats()
    
    def _process_data(self, data, addr):
        """处理接收到的UDP数据包"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # 提取命令标识符（如果有）
        command_id = "Unknown"
        if len(data) >= 4:
            try:
                command_id = data[:4].decode('ascii', errors='replace')
                # 更新命令类型统计
                if command_id in self.stats["command_types"]:
                    self.stats["command_types"][command_id] += 1
                else:
                    self.stats["command_types"][command_id] = 1
            except:
                pass
        
        # 显示数据包信息
        print(f"\n[{timestamp}] 接收到数据包 #{self.packet_count}")
        print(f"发送方: {addr[0]}:{addr[1]}")
        print(f"数据大小: {len(data)} 字节")
        print(f"命令ID: {command_id}")
        
        # 解析数据
        self._parse_data(data)
        
        # 记录到日志文件
        if self.enable_logging:
            self._log_data(timestamp, addr, data, command_id)
    
    def _parse_data(self, data):
        """解析UDP数据包内容"""
        try:
            # 显示十六进制原始数据
            hex_data = binascii.hexlify(data).decode()
            print(f"原始数据: {hex_data}")
            
            # 尝试解析ASCII内容
            try:
                ascii_str = data.decode('ascii', errors='replace')
                print(f"ASCII解析: {ascii_str}")
            except:
                pass
            
            # 解析二进制结构
            if len(data) >= 4:
                # 假设前4字节是命令标识
                command = data[:4].decode('ascii', errors='replace')
                
                # 从第5个字节开始尝试解析整数和浮点数值
                pos = 4
                values = []
                
                while pos + 4 <= len(data):
                    try:
                        # 解析为整数
                        int_val = struct.unpack('<i', data[pos:pos+4])[0]
                        # 解析为浮点数
                        float_val = struct.unpack('<f', data[pos:pos+4])[0]
                        
                        values.append({
                            "position": f"{pos}-{pos+3}",
                            "int": int_val,
                            "float": float_val
                        })
                        
                        pos += 4
                    except:
                        break
                
                # 显示解析结果
                if values:
                    print("解析值:")
                    for val in values:
                        print(f"  位置 {val['position']}: 整数={val['int']}, 浮点数={val['float']}")
            
            print("-" * 60)
            
        except Exception as e:
            print(f"解析数据失败: {e}")
            print("-" * 60)
    
    def _log_data(self, timestamp, addr, data, command_id):
        """将数据包记录到日志文件"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                hex_data = binascii.hexlify(data).decode()
                log_entry = f"{timestamp}|{addr[0]}:{addr[1]}|{len(data)}|{command_id}|{hex_data}\n"
                f.write(log_entry)
        except Exception as e:
            print(f"写入日志失败: {e}")
    
    def _status_display_thread(self):
        """状态显示线程，定期显示接收统计信息"""
        last_count = 0
        last_time = datetime.datetime.now()
        
        while self.running:
            time.sleep(5)  # 每5秒更新一次
            
            now = datetime.datetime.now()
            elapsed = (now - last_time).total_seconds()
            
            # 计算接收速率
            new_packets = self.packet_count - last_count
            rate = new_packets / elapsed if elapsed > 0 else 0
            
            # 更新上次统计
            last_count = self.packet_count
            last_time = now
            
            # 显示状态信息
            if self.packet_count > 0:
                total_elapsed = (now - self.stats["start_time"]).total_seconds()
                avg_rate = self.packet_count / total_elapsed if total_elapsed > 0 else 0
                
                print(f"\n--- 状态更新 ---")
                print(f"总计接收: {self.packet_count} 个数据包 ({self.stats['total_bytes']/1024:.2f} KB)")
                print(f"当前接收速率: {rate:.2f} 包/秒")
                print(f"平均接收速率: {avg_rate:.2f} 包/秒")
                
                if self.last_packet_time:
                    last_recv = (now - self.last_packet_time).total_seconds()
                    print(f"距上次接收: {last_recv:.1f} 秒")
                
                # 显示命令类型统计
                if self.stats["command_types"]:
                    print("命令类型统计:")
                    for cmd, count in self.stats["command_types"].items():
                        print(f"  {cmd}: {count} 次")
                
                print("-" * 60)
    
    def _display_final_stats(self):
        """显示最终统计信息"""
        if self.stats["start_time"]:
            end_time = datetime.datetime.now()
            total_elapsed = (end_time - self.stats["start_time"]).total_seconds()
            
            print("\n=== 最终统计信息 ===")
            print(f"监听时长: {total_elapsed:.1f} 秒")
            print(f"总计接收: {self.stats['total_packets']} 个数据包 ({self.stats['total_bytes']/1024:.2f} KB)")
            
            if total_elapsed > 0:
                avg_rate = self.stats["total_packets"] / total_elapsed
                print(f"平均接收速率: {avg_rate:.2f} 包/秒")
            
            if self.stats["command_types"]:
                print("\n命令类型统计:")
                for cmd, count in sorted(self.stats["command_types"].items(), key=lambda x: x[1], reverse=True):
                    print(f"  {cmd}: {count} 次 ({count/self.stats['total_packets']*100:.1f}%)")
            
            if self.enable_logging and os.path.exists(self.log_file):
                print(f"\n接收日志已保存至: {os.path.abspath(self.log_file)}")
            
            if self.stats["total_packets"] == 0:
                print("\n未接收到任何数据包，可能的原因:")
                print("1. Resim未启动或未进入模拟状态")
                print("2. Resim未启用DS模式 (使用--ds-mode启动参数)")
                print("3. Resim未正确配置UDP通信")
                print("4. 防火墙阻止了UDP通信")
                print("5. 端口配置错误 (当前监听端口: {})".format(self.port))


def main():
    print("Resim UDP 消息监听器")
    print("=" * 60)
    
    # 解析命令行参数
    port = LISTEN_PORT
    
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
            print(f"使用指定端口: {port}")
        except ValueError:
            print(f"无效的端口号: {sys.argv[1]}，使用默认端口: {LISTEN_PORT}")
    else:
        print(f"使用默认端口: {port}")
    
    # 创建并启动监听器
    receiver = UDPReceiver(port=port)
    receiver.start()


if __name__ == "__main__":
    main()