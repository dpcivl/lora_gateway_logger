#!/bin/bash

# 라즈베리파이 배포 스크립트
# 사용법: ./deploy.sh [raspberry-pi-ip] [optional-username]

set -e

# 설정
RASPBERRY_IP=${1:-"192.168.0.110"}
USERNAME=${2:-"pi"}
REMOTE_DIR="/home/$USERNAME/lora_gateway_logger"
LOCAL_DIR="."

echo "=== LoRa Gateway Logger 배포 스크립트 ==="
echo "대상: $USERNAME@$RASPBERRY_IP:$REMOTE_DIR"

# 1. 라즈베리파이 연결 테스트
echo "1. 라즈베리파이 연결 테스트..."
if ! ping -c 1 $RASPBERRY_IP > /dev/null 2>&1; then
    echo "오류: $RASPBERRY_IP 에 연결할 수 없습니다."
    exit 1
fi

# 2. SSH 연결 테스트
echo "2. SSH 연결 테스트..."
if ! ssh -o ConnectTimeout=10 $USERNAME@$RASPBERRY_IP "echo 'SSH 연결 성공'" > /dev/null 2>&1; then
    echo "오류: SSH 연결에 실패했습니다. SSH 키가 설정되어 있는지 확인하세요."
    exit 1
fi

# 3. 원격 디렉토리 생성
echo "3. 원격 디렉토리 생성..."
ssh $USERNAME@$RASPBERRY_IP "mkdir -p $REMOTE_DIR/logs"

# 4. 파일 동기화
echo "4. 파일 동기화..."
rsync -avz --exclude='*.log' --exclude='uplink_data_*.json' --exclude='__pycache__' \
    --exclude='.git' --exclude='logs/' \
    $LOCAL_DIR/ $USERNAME@$RASPBERRY_IP:$REMOTE_DIR/

# 5. 원격에서 의존성 설치
echo "5. Python 패키지 설치..."
ssh $USERNAME@$RASPBERRY_IP "cd $REMOTE_DIR && pip3 install -r requirements.txt"

# 6. systemd 서비스 파일 생성
echo "6. systemd 서비스 설정..."
ssh $USERNAME@$RASPBERRY_IP "sudo tee /etc/systemd/system/lora-gateway-logger.service > /dev/null << 'EOF'
[Unit]
Description=LoRa Gateway Logger
After=network.target

[Service]
Type=simple
User=$USERNAME
WorkingDirectory=$REMOTE_DIR
ExecStart=/usr/bin/python3 $REMOTE_DIR/main.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF"

# 7. 서비스 활성화 및 시작
echo "7. 서비스 활성화..."
ssh $USERNAME@$RASPBERRY_IP "sudo systemctl daemon-reload && sudo systemctl enable lora-gateway-logger.service"

# 8. 현재 실행 중인 서비스가 있다면 재시작
echo "8. 서비스 재시작..."
ssh $USERNAME@$RASPBERRY_IP "sudo systemctl restart lora-gateway-logger.service"

# 9. 서비스 상태 확인
echo "9. 배포 완료 - 서비스 상태 확인:"
ssh $USERNAME@$RASPBERRY_IP "sudo systemctl status lora-gateway-logger.service --no-pager"

echo ""
echo "=== 배포 완료 ==="
echo "다음 명령어로 로그를 실시간 확인할 수 있습니다:"
echo "ssh $USERNAME@$RASPBERRY_IP 'sudo journalctl -u lora-gateway-logger.service -f'"
echo ""
echo "서비스 제어 명령어:"
echo "  시작: ssh $USERNAME@$RASPBERRY_IP 'sudo systemctl start lora-gateway-logger.service'"
echo "  중지: ssh $USERNAME@$RASPBERRY_PI 'sudo systemctl stop lora-gateway-logger.service'"
echo "  재시작: ssh $USERNAME@$RASPBERRY_IP 'sudo systemctl restart lora-gateway-logger.service'"