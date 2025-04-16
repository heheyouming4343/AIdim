import gymnasium as gym
from gymnasium import spaces
import numpy as np
import socket
import struct
import time
from typing import Optional, Tuple, Dict, Any
from stable_baselines3 import PPO

class LaneChangeDirection:
    LEFT = 0
    RIGHT = 1

class LaneChangeMode:
    CHECK_RISK = 0
    FORCE_CHANGE = 1

class ResimEnv(gym.Env):
    """
    连接到已运行的QT平台Resim的强化学习环境
    """
    metadata = {'render_modes': ['human']}
    
    def __init__(self, 
                 agent_id: int = 10,
                 ip: str = "127.0.0.1", 
                 port: int = 20001,
                 debug: bool = True):
        super().__init__()
        
        # 通信设置
        self.agent_id = agent_id
        self.ip = ip
        self.send_port = port        # 发送到Resim的端口(20001)
        self.receive_port = 20000    # 从Resim接收数据的端口
        self.debug = debug
        
        # 创建UDP Socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # 设置动作空间: [加速度, 制动, 转向, 变道指令]
        # 加速度: [0,1], 制动: [0,1], 转向: [-1,1], 变道: [-1,1]
        self.action_space = spaces.Box(
            low=np.array([0.0, 0.0, -1.0, -1.0]),
            high=np.array([1.0, 1.0, 1.0, 1.0]),
            dtype=np.float32
        )
        
        # 设置状态空间
        self.observation_space = spaces.Box(
            low=np.array([-np.inf] * 10),
            high=np.array([np.inf] * 10),
            dtype=np.float32
        )
        
        # 内部状态
        self.max_steps = 1000
        self.current_step = 0
        self.last_state = np.zeros(10, dtype=np.float32)
        
        if self.debug:
            print(f"初始化完成，将发送命令到 {self.ip}:{self.send_port}")
    
    def _send_command(self, command: bytes) -> None:
        """发送命令到Resim"""
        try:
            if self.debug:
                print(f"发送命令: {command.hex()}")
            
            # 创建一个新的socket进行发送，避免连接问题
            send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            send_sock.sendto(command, (self.ip, self.send_port))
            send_sock.close()
        except Exception as e:
            print(f"发送命令失败: {e}")
    
    def _create_lane_change_command(self, agent_id: int, direction: int, mode: int = 0) -> bytes:
        """
        创建车道变换命令 - 按照resim_lane_change.py中的格式
        
        格式: 'FCAL' + agent_id(4字节) + direction(4字节) + mode(4字节)
        """
        command = b'FCAL'  # 前缀标识
        command += struct.pack('<i', agent_id)  # 车辆ID
        command += struct.pack('<i', direction)  # 变道方向: 0=左, 1=右
        command += struct.pack('<i', mode)  # 变道模式: 0=检查风险, 1=强制变道
        
        return command
    
    def _create_control_command(self, agent_id: int, accel: float, brake: float, steer: float) -> bytes:
        """
        创建基本控制命令 - 推测Resim期望的格式
        """
        # 这部分需要根据Resim的实际期望格式调整
        # 这里假设基本控制命令格式为 'FCON' + agent_id + accel + brake + steer
        command = b'FCON'
        command += struct.pack('<i', agent_id)
        command += struct.pack('<f', accel)
        command += struct.pack('<f', brake)
        command += struct.pack('<f', steer)
        
        return command
    
    def _create_reset_command(self) -> bytes:
        """创建重置命令"""
        return b'FRS'  # 假设重置命令前缀为F
    
    def _create_start_command(self) -> bytes:
        """创建开始模拟命令"""
        return b'FCS'  # 假设开始命令前缀为F
    
    def _get_state(self) -> np.ndarray:
        """
        获取当前状态 - 这需要与Resim的实际状态格式对应
        由于我们没有实际接收数据，这里返回模拟状态
        """
        # 在实际应用中，应该使用socket接收数据并解析
        # 这里使用模拟数据
        state = np.random.rand(10).astype(np.float32)
        
        # 标准化一些值以使其更合理
        state[4] = 20.0 + np.random.normal(0, 2)  # 速度约为20 m/s
        state[5] = np.random.normal(0, 0.5)  # 横向偏差
        
        self.last_state = state
        return state
    
    def _calculate_reward(self, state: np.ndarray, action: np.ndarray) -> float:
        """计算奖励函数"""
        reward = 0.0
        
        # 车道保持奖励
        lateral_deviation = abs(state[5])  # 横向偏差
        reward -= lateral_deviation * 2.0
        
        # 速度匹配奖励
        current_speed = state[4]
        target_speed = 20.0
        speed_diff = abs(current_speed - target_speed)
        reward -= speed_diff * 0.5
        
        # 变道奖励
        if abs(action[3]) > 0.5:  # 如果执行了变道
            if lateral_deviation < 0.5:  # 变道成功
                reward += 10.0
            else:  # 变道失败
                reward -= 5.0
        
        # 平滑控制奖励
        control_smoothness = -(action[0]**2 + action[1]**2 + action[2]**2)
        reward += control_smoothness * 0.1
        
        return reward
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """执行一步动作"""
        self.current_step += 1
        
        # 处理车道变换动作
        if abs(action[3]) > 0.5:
            direction = LaneChangeDirection.LEFT if action[3] < 0 else LaneChangeDirection.RIGHT
            mode = LaneChangeMode.FORCE_CHANGE  # 使用强制变道以确保执行
            
            lane_change_cmd = self._create_lane_change_command(
                agent_id=self.agent_id,
                direction=direction,
                mode=mode
            )
            
            self._send_command(lane_change_cmd)
            if self.debug:
                print(f"执行变道: {'左' if direction == LaneChangeDirection.LEFT else '右'}")
        
        # 发送基本控制命令
        control_cmd = self._create_control_command(
            agent_id=self.agent_id,
            accel=float(action[0]),
            brake=float(action[1]),
            steer=float(action[2])
        )
        self._send_command(control_cmd)
        
        # 等待Resim处理命令
        time.sleep(0.05)
        
        # 获取新状态
        new_state = self._get_state()
        
        # 计算奖励
        reward = self._calculate_reward(new_state, action)
        
        # 判断是否结束
        terminated = False
        truncated = self.current_step >= self.max_steps
        
        # 如果偏离太远，终止
        if abs(new_state[5]) > 3.0:
            terminated = True
            reward -= 20.0
        
        info = {
            "step": self.current_step,
            "agent_id": self.agent_id
        }
        
        return new_state, reward, terminated, truncated, info
    
    def reset(self, seed=None, options=None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """重置环境"""
        super().reset(seed=seed)
        
        self.current_step = 0
        
        # 发送重置命令
        self._send_command(self._create_reset_command())
        time.sleep(0.5)
        
        # 发送开始命令
        self._send_command(self._create_start_command())
        time.sleep(0.1)
        
        # 获取初始状态
        initial_state = self._get_state()
        
        return initial_state, {}
    
    def close(self):
        """关闭环境"""
        if hasattr(self, 'socket'):
            self.socket.close()
            
def train_resim_agent():
    """训练Resim代理"""
    print("====== Resim RL 训练 ======")
    print("请确保Resim已在QT平台启动，并启用了DS模式")
    input("按Enter继续...")
    
    # 创建环境
    env = ResimEnv(agent_id=10, debug=True)
    
    # 设置模型
    model = PPO(
        "MlpPolicy", 
        env, 
        verbose=1,
        learning_rate=3e-4,
        tensorboard_log="./resim_tensorboard/"
    )
    
    try:
        # 训练模型
        model.learn(
            total_timesteps=100000,
            progress_bar=True
        )
        
        # 保存模型
        model.save("resim_model")
        print("训练完成，模型已保存")
        
    except KeyboardInterrupt:
        print("\n训练被中断")
        model.save("resim_interrupted_model")
        
    finally:
        env.close()

if __name__ == "__main__":
    train_resim_agent()