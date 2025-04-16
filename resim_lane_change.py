import socket
import struct
import time
import threading
from enum import Enum
import logging
import sys

class LaneChangeDirection(Enum):
    LEFT = 0  # 修改为0，与Resim代码保持一致
    RIGHT = 1  # 修改为1，与Resim代码保持一致

class LaneChangeMode(Enum):
    CHECK_RISK = 0    # 检查风险后变道
    FORCE_CHANGE = 1  # 强制变道，忽略风险

class ResimLaneChanger:
    def __init__(self):
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,  # 改回INFO级别，减少日志输出
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("ResimLaneChanger")
        
        # Re:sim配置 - 与Lanechange.sysfile保持一致
        self.resim_ip = "127.0.0.1"
        self.send_port = 20001    # 修改为20001，直接发送到Re:sim的接收端口
        self.receive_port = 20000 # 修改为20000，从Re:sim接收消息的端口
        
        # 周期变道设置
        self.cycle_active = False
        self.cycle_thread = None
        
    def connect(self):
        """建立UDP连接"""
        try:
            # 每次发送消息时创建新的UDP socket，避免连接被关闭的问题
            self.logger.info(f"UDP客户端准备就绪，将发送到 {self.resim_ip}:{self.send_port}")
            return True
        except Exception as e:
            self.logger.error(f"UDP客户端初始化失败: {e}")
            return False

    def request_lane_change(self, agent_id: int, direction: LaneChangeDirection, mode: LaneChangeMode = LaneChangeMode.CHECK_RISK):
        """
        请求agent换道
        :param agent_id: agent的ID
        :param direction: 换道方向 (LEFT/RIGHT)
        :param mode: 换道模式 (检查风险/强制变道)
        """
        try:
            # 创建新的套接字
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # 使用正确的命令格式: 'FCAL' + agent_id(4字节) + direction(4字节) + mode(4字节)
            command = b'FCAL'
            command += struct.pack('<i', agent_id)
            command += struct.pack('<i', direction.value)
            command += struct.pack('<i', mode.value)
            
            self.logger.info(f"发送换道命令: FCAL (agent={agent_id}, direction={direction.name}, mode={mode.name})")
            self.logger.debug(f"原始命令数据: {command.hex()}")
            
            # 发送到Resim的接收端口
            sock.sendto(command, (self.resim_ip, self.send_port))
            
            # 关闭套接字
            sock.close()
            return True
            
        except Exception as e:
            self.logger.error(f"发送换道请求失败: {e}")
            return False

    def request_assigned_lane_change(self, agent_id: int, direction: LaneChangeDirection, 
                                   mode: LaneChangeMode = LaneChangeMode.CHECK_RISK, 
                                   distance: float = 50.0):
        """
        请求指定距离的换道
        :param agent_id: agent的ID
        :param direction: 换道方向
        :param mode: 换道模式
        :param distance: 换道距离（米）
        """
        try:
            # 创建新的套接字
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # 使用正确的命令格式: 'FCAL' + agent_id(4字节) + direction(4字节) + mode(4字节) + distance(4字节)
            command = b'FCAL'
            command += struct.pack('<i', agent_id)
            command += struct.pack('<i', direction.value)
            command += struct.pack('<i', mode.value)
            command += struct.pack('<f', distance)
            
            self.logger.info(f"发送指定距离换道命令: FCAL (agent={agent_id}, direction={direction.name}, mode={mode.name}, distance={distance})")
            self.logger.debug(f"原始命令数据: {command.hex()}")
            
            # 发送到Resim的接收端口
            sock.sendto(command, (self.resim_ip, self.send_port))
            
            # 关闭套接字
            sock.close()
            return True
            
        except Exception as e:
            self.logger.error(f"发送指定距离换道请求失败: {e}")
            return False

    def start_cyclic_lane_change(self, agent_id: int, interval: float = 5.0, 
                              alternate_direction: bool = True):
        """
        开始周期性换道
        :param agent_id: agent的ID
        :param interval: 换道间隔时间（秒）
        :param alternate_direction: 是否交替左右换道
        """
        if self.cycle_active:
            self.logger.warning("周期换道已经在运行中")
            return False
        
        self.cycle_active = True
        self.cycle_thread = threading.Thread(
            target=self._cyclic_lane_change_worker,
            args=(agent_id, interval, alternate_direction)
        )
        self.cycle_thread.daemon = True
        self.cycle_thread.start()
        
        self.logger.info(f"已启动周期换道: ID={agent_id}, 间隔={interval}秒, 交替方向={alternate_direction}")
        return True
    
    def stop_cyclic_lane_change(self):
        """停止周期性换道"""
        if not self.cycle_active:
            self.logger.warning("没有正在运行的周期换道")
            return False
        
        self.cycle_active = False
        if self.cycle_thread:
            self.cycle_thread.join(timeout=1.0)
            self.cycle_thread = None
        
        self.logger.info("已停止周期换道")
        return True
    
    def _cyclic_lane_change_worker(self, agent_id: int, interval: float, alternate_direction: bool):
        """周期换道工作线程"""
        current_direction = LaneChangeDirection.LEFT
        
        try:
            while self.cycle_active:
                # 发送换道请求
                self.logger.info(f"执行周期换道: ID={agent_id}, 方向={'左' if current_direction==LaneChangeDirection.LEFT else '右'}")
                self.request_lane_change(
                    agent_id=agent_id,
                    direction=current_direction,
                    mode=LaneChangeMode.FORCE_CHANGE
                )
                
                # 等待指定间隔
                time.sleep(interval)
                
                # 如果需要交替方向，切换方向
                if alternate_direction:
                    if current_direction == LaneChangeDirection.LEFT:
                        current_direction = LaneChangeDirection.RIGHT
                    else:
                        current_direction = LaneChangeDirection.LEFT
        
        except Exception as e:
            self.logger.error(f"周期换道线程出错: {e}")
            self.cycle_active = False

    def close(self):
        """关闭连接"""
        if self.cycle_active:
            self.stop_cyclic_lane_change()
        
        self.logger.info("连接已关闭")

def main():
    """自动运行，无需用户输入，直接开始循环变道"""
    changer = ResimLaneChanger()
    
    # 连接到Resim
    if not changer.connect():
        print("无法连接到Resim，程序退出")
        return
    
    # 默认使用agent ID 10开始周期变道
    agent_id = 10
    interval = 5.0  # 5秒变道一次
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        try:
            agent_id = int(sys.argv[1])
        except ValueError:
            print(f"无效的agent ID: {sys.argv[1]}，使用默认值10")
    
    if len(sys.argv) > 2:
        try:
            interval = float(sys.argv[2])
        except ValueError:
            print(f"无效的变道间隔: {sys.argv[2]}，使用默认值5.0秒")
    
    print(f"开始自动循环变道，使用agent ID: {agent_id}, 变道间隔: {interval}秒")
    print("按Ctrl+C退出")
    
    try:
        # 首先尝试单次变道以测试连接
        print("尝试单次变道测试...")
        changer.request_lane_change(
            agent_id=agent_id,
            direction=LaneChangeDirection.LEFT,
            mode=LaneChangeMode.FORCE_CHANGE
        )
        
        time.sleep(2)  # 等待2秒观察效果
        
        # 开始周期变道
        changer.start_cyclic_lane_change(
            agent_id=agent_id,
            interval=interval,
            alternate_direction=True
        )
        
        # 保持程序运行，直到用户按Ctrl+C
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n用户中断，程序退出")
    finally:
        # 确保关闭连接
        changer.close()
        print("程序已退出")

if __name__ == "__main__":
    main() 