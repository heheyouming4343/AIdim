import socket
import struct
import time
import logging
import binascii
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("UDPSenderTest")

# Re:sim配置
RESIM_IP = "127.0.0.1"
SEND_PORT = 20001  # 发送到Re:sim的接收端口

def send_udp_packet(data, ip=RESIM_IP, port=SEND_PORT):
    """发送UDP数据包"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(data, (ip, port))
        sock.close()
        
        # 打印16进制数据用于调试
        hex_data = binascii.hexlify(data).decode('ascii')
        logger.info(f"已发送UDP数据到 {ip}:{port}: {hex_data}")
        return True
    except Exception as e:
        logger.error(f"发送UDP数据包失败: {e}")
        return False

def test_lane_change_commands():
    """测试各种换道命令格式"""
    # 定义测试用的agent_id, direction和mode
    agent_id = 10
    direction = 0  # 0=左, 1=右
    mode = 1       # 0=检查风险, 1=强制变道
    
    # 测试不同的命令格式，看哪一个能被Resim接受
    test_commands = [
        # 测试1: "CL" + 参数 (原始C++代码中的格式)
        (b'CL' + struct.pack('<iii', agent_id, direction, mode), 
         "格式1: 'CL' + agent_id + direction + mode"),
        
        # 测试2: "FCAL" + 参数 (Python脚本中使用的格式)
        (b'FCAL' + struct.pack('<iii', agent_id, direction, mode),
         "格式2: 'FCAL' + agent_id + direction + mode"),
        
        # 测试3: "ACL" + 参数 (可能的格式变体)
        (b'ACL' + struct.pack('<iii', agent_id, direction, mode),
         "格式3: 'ACL' + agent_id + direction + mode"),
        
        # 测试4: 纯"CL" (简单测试，看是否接受无参数命令)
        (b'CL',
         "格式4: 纯'CL'命令"),
        
        # 测试5: 不同的字节顺序
        (b'CL' + struct.pack('>iii', agent_id, direction, mode),
         "格式5: 'CL' + agent_id + direction + mode (大端字节序)"),
        
        # 测试6: "CS" (模拟开始模拟命令，看能否激活Resim)
        (b'CS',
         "格式6: 'CS' 开始模拟命令"),
        
        # 测试7: 相同参数不同前缀
        (b'LC' + struct.pack('<iii', agent_id, direction, mode),
         "格式7: 'LC' + agent_id + direction + mode"),
        
        # 测试8: 添加更多参数 (包含距离参数)
        (b'CL' + struct.pack('<iiif', agent_id, direction, mode, 50.0),
         "格式8: 'CL' + agent_id + direction + mode + distance"),
        
        # 测试9: 前缀与参数间添加分隔符
        (b'CL|' + struct.pack('<iii', agent_id, direction, mode),
         "格式9: 'CL|' + agent_id + direction + mode"),
        
        # 测试10: 尝试其他可能的命令格式
        (b'LANE' + struct.pack('<iii', agent_id, direction, mode),
         "格式10: 'LANE' + agent_id + direction + mode")
    ]
    
    logger.info("开始测试各种换道命令格式...")
    
    # 逐一发送测试命令
    for command_data, description in test_commands:
        logger.info(f"测试 - {description}")
        if send_udp_packet(command_data):
            logger.info("发送成功")
        else:
            logger.info("发送失败")
        
        # 暂停2秒，以便观察Resim的反应
        time.sleep(2)
    
    logger.info("所有测试命令已发送")

def main():
    logger.info("UDP发送测试程序启动")
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        # 如果有命令行参数，只发送特定格式的命令
        try:
            test_idx = int(sys.argv[1]) - 1
            if test_idx < 0 or test_idx >= 10:
                raise ValueError("测试索引必须在1-10之间")
                
            agent_id = 10
            direction = 0
            mode = 1
            
            # 生成特定的测试命令
            test_commands = [
                b'CL' + struct.pack('<iii', agent_id, direction, mode),
                b'FCAL' + struct.pack('<iii', agent_id, direction, mode),
                b'ACL' + struct.pack('<iii', agent_id, direction, mode),
                b'CL',
                b'CL' + struct.pack('>iii', agent_id, direction, mode),
                b'CS',
                b'LC' + struct.pack('<iii', agent_id, direction, mode),
                b'CL' + struct.pack('<iiif', agent_id, direction, mode, 50.0),
                b'CL|' + struct.pack('<iii', agent_id, direction, mode),
                b'LANE' + struct.pack('<iii', agent_id, direction, mode)
            ]
            
            command = test_commands[test_idx]
            logger.info(f"发送测试{test_idx+1}的命令...")
            send_udp_packet(command)
            
        except (ValueError, IndexError) as e:
            logger.error(f"参数错误: {e}")
            logger.info("使用方法: python udp_sender_test.py [测试编号1-10]")
            return
    else:
        # 没有命令行参数，运行所有测试
        test_lane_change_commands()
    
    logger.info("测试完成")

if __name__ == "__main__":
    main() 