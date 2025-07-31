#!/usr/bin/env python3
"""
원격 디버깅을 위한 도구들
"""

import argparse
import subprocess
import json
import time
from datetime import datetime

def tail_remote_logs(host, username="pi", service_name="lora-gateway-logger"):
    """라즈베리파이의 서비스 로그를 실시간으로 확인"""
    cmd = f"ssh {username}@{host} 'sudo journalctl -u {service_name}.service -f'"
    print(f"실행: {cmd}")
    subprocess.run(cmd, shell=True)

def check_remote_status(host, username="pi", service_name="lora-gateway-logger"):
    """라즈베리파이의 서비스 상태 확인"""
    commands = [
        f"sudo systemctl status {service_name}.service --no-pager",
        "ps aux | grep python",
        "netstat -tlnp | grep 1883",
        "df -h",
        "free -h",
        "uptime"
    ]
    
    for cmd in commands:
        print(f"\n=== {cmd} ===")
        full_cmd = f"ssh {username}@{host} '{cmd}'"
        subprocess.run(full_cmd, shell=True)

def collect_remote_logs(host, username="pi", output_dir="./remote_logs"):
    """라즈베리파이에서 로그 파일들을 수집"""
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 수집할 파일들
    files_to_collect = [
        "/home/pi/lora_gateway_logger/*.log",
        "/home/pi/lora_gateway_logger/uplink_data_*.json"
    ]
    
    for file_pattern in files_to_collect:
        cmd = f"scp {username}@{host}:{file_pattern} {output_dir}/ 2>/dev/null || true"
        print(f"수집: {file_pattern}")
        subprocess.run(cmd, shell=True)
    
    # systemd 로그 수집
    log_file = f"{output_dir}/systemd_log_{timestamp}.txt"
    cmd = f"ssh {username}@{host} 'sudo journalctl -u lora-gateway-logger.service --no-pager' > {log_file}"
    subprocess.run(cmd, shell=True)
    
    print(f"로그 수집 완료: {output_dir}")

def send_test_data(host, username="pi", count=5):
    """라즈베리파이에 테스트 데이터 전송"""
    cmd = f"""ssh {username}@{host} 'cd /home/{username}/lora_gateway_logger && python3 mock_mqtt_publisher.py --count {count} --interval 3'"""
    print(f"테스트 데이터 전송: {count}개")
    subprocess.run(cmd, shell=True)

def remote_service_control(host, username="pi", action="status", service_name="lora-gateway-logger"):
    """라즈베리파이 서비스 제어"""
    valid_actions = ["start", "stop", "restart", "status", "enable", "disable"]
    if action not in valid_actions:
        print(f"유효하지 않은 액션: {action}. 사용 가능: {valid_actions}")
        return
    
    cmd = f"ssh {username}@{host} 'sudo systemctl {action} {service_name}.service'"
    if action == "status":
        cmd += " --no-pager"
    
    print(f"서비스 {action} 실행...")
    subprocess.run(cmd, shell=True)

def analyze_uplink_data(file_path):
    """업링크 데이터 파일 분석"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"=== {file_path} 분석 결과 ===")
        print(f"총 레코드 수: {len(lines)}")
        
        if lines:
            # 첫 번째와 마지막 타임스탬프
            first_record = json.loads(lines[0])
            last_record = json.loads(lines[-1])
            
            print(f"첫 번째 레코드: {first_record['timestamp']}")
            print(f"마지막 레코드: {last_record['timestamp']}")
            
            # 애플리케이션/디바이스 통계
            apps = set()
            devices = set()
            for line in lines:
                data = json.loads(line)
                apps.add(data['application_id'])
                devices.add(data['device_id'])
            
            print(f"애플리케이션 수: {len(apps)} ({list(apps)})")
            print(f"디바이스 수: {len(devices)} ({list(devices)})")
            
            # 페이로드 크기 통계
            sizes = []
            for line in lines:
                data = json.loads(line)
                if 'raw_payload_size' in data:
                    sizes.append(data['raw_payload_size'])
            
            if sizes:
                print(f"페이로드 크기 - 평균: {sum(sizes)/len(sizes):.1f}, "
                      f"최소: {min(sizes)}, 최대: {max(sizes)}")
        
    except Exception as e:
        print(f"파일 분석 오류: {e}")

def main():
    parser = argparse.ArgumentParser(description='LoRa Gateway Logger 디버깅 도구')
    parser.add_argument('command', choices=[
        'tail-logs', 'status', 'collect-logs', 'test-data', 
        'service', 'analyze'
    ], help='실행할 명령')
    
    parser.add_argument('--host', required=True, help='라즈베리파이 IP 주소')
    parser.add_argument('--username', default='pi', help='SSH 사용자명')
    parser.add_argument('--service', default='lora-gateway-logger', help='서비스명')
    parser.add_argument('--action', help='서비스 제어 액션 (start/stop/restart/status)')
    parser.add_argument('--count', type=int, default=5, help='테스트 데이터 개수')
    parser.add_argument('--file', help='분석할 파일 경로')
    
    args = parser.parse_args()
    
    if args.command == 'tail-logs':
        tail_remote_logs(args.host, args.username, args.service)
    elif args.command == 'status':
        check_remote_status(args.host, args.username, args.service)
    elif args.command == 'collect-logs':
        collect_remote_logs(args.host, args.username)
    elif args.command == 'test-data':
        send_test_data(args.host, args.username, args.count)
    elif args.command == 'service':
        if not args.action:
            print("--action 인자가 필요합니다 (start/stop/restart/status)")
            return
        remote_service_control(args.host, args.username, args.action, args.service)
    elif args.command == 'analyze':
        if not args.file:
            print("--file 인자가 필요합니다")
            return
        analyze_uplink_data(args.file)

if __name__ == "__main__":
    main()