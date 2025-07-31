#!/bin/bash

# ssh-agent를 사용한 배포 스크립트
# 사용법: ./deploy_with_agent.sh [raspberry-pi-ip] [optional-username]

set -e

# 설정
RASPBERRY_IP=${1:-"192.168.0.110"}
USERNAME=${2:-"pi"}
REMOTE_DIR="/home/$USERNAME/lora_gateway_logger"
LOCAL_DIR="."

echo "=== LoRa Gateway Logger 배포 스크립트 (ssh-agent 사용) ==="
echo "대상: $USERNAME@$RASPBERRY_IP:$REMOTE_DIR"

# ssh-agent 시작 및 키 추가
echo "1. SSH agent 설정..."
eval $(ssh-agent -s)

echo "SSH 키 passphrase를 입력하세요 (이번 한 번만 입력하면 됩니다):"
ssh-add ~/.ssh/id_rsa

echo ""
echo "2. SSH 연결 테스트..."
if ! ssh -o ConnectTimeout=10 $USERNAME@$RASPBERRY_IP "echo 'SSH 연결 성공'" > /dev/null 2>&1; then
    echo "오류: SSH 연결에 실패했습니다."
    kill $SSH_AGENT_PID
    exit 1
fi

echo "3. 원격 디렉토리 생성..."
ssh $USERNAME@$RASPBERRY_IP "mkdir -p $REMOTE_DIR/logs"

echo "4. 파일 동기화..."
# Windows Git Bash에서는 scp 사용
if command -v rsync >/dev/null 2>&1; then
    rsync -avz --exclude='*.log' --exclude='uplink_data_*.json' --exclude='__pycache__' \
        --exclude='.git' --exclude='logs/' \
        $LOCAL_DIR/ $USERNAME@$RASPBERRY_IP:$REMOTE_DIR/
else
    echo "rsync가 없어서 scp 사용..."
    # 메인 파일들 전송
    scp main.py requirements.txt config.py models.py database.py $USERNAME@$RASPBERRY_IP:$REMOTE_DIR/ 2>/dev/null || true
    
    # core 디렉토리 전송
    echo "core/ 디렉토리 전송..."
    ssh $USERNAME@$RASPBERRY_IP "mkdir -p $REMOTE_DIR/core"
    scp core/*.py $USERNAME@$RASPBERRY_IP:$REMOTE_DIR/core/ 2>/dev/null || true
    
    # 추가 Python 파일들이 있다면 함께 전송
    if ls test_*.py >/dev/null 2>&1; then
        scp test_*.py $USERNAME@$RASPBERRY_IP:$REMOTE_DIR/ 2>/dev/null || true
    fi
fi

echo "5. Python 패키지 설치..."
ssh $USERNAME@$RASPBERRY_IP "cd $REMOTE_DIR && pip3 install -r requirements.txt"

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

echo "7. 서비스 활성화..."
ssh $USERNAME@$RASPBERRY_IP "sudo systemctl daemon-reload && sudo systemctl enable lora-gateway-logger.service"

echo "8. 서비스 재시작..."
ssh $USERNAME@$RASPBERRY_IP "sudo systemctl restart lora-gateway-logger.service"

echo "9. 배포 완료 - 서비스 상태 확인:"
ssh $USERNAME@$RASPBERRY_IP "sudo systemctl status lora-gateway-logger.service --no-pager"

# ssh-agent 종료
kill $SSH_AGENT_PID

echo ""
echo "=== 배포 완료 ==="
echo "다음 명령어로 로그를 실시간 확인할 수 있습니다:"
echo "ssh $USERNAME@$RASPBERRY_IP 'sudo journalctl -u lora-gateway-logger.service -f'"
echo ""
echo "서비스 제어 명령어:"
echo "  시작: ssh $USERNAME@$RASPBERRY_IP 'sudo systemctl start lora-gateway-logger.service'"
echo "  중지: ssh $USERNAME@$RASPBERRY_IP 'sudo systemctl stop lora-gateway-logger.service'"
echo "  재시작: ssh $USERNAME@$RASPBERRY_IP 'sudo systemctl restart lora-gateway-logger.service'"