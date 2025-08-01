# 라즈베리파이 환경 정보

## 개요

LoRa Gateway Logger는 라즈베리파이에서 실행되도록 설계되었습니다. 이 문서는 라즈베리파이 환경 설정과 최적화 방법을 설명합니다.

## 라즈베리파이 사양

### 권장 사양
- **모델**: Raspberry Pi 4 Model B (2GB 이상)
- **OS**: Raspberry Pi OS (64-bit) 또는 Ubuntu 20.04 LTS
- **저장소**: Class 10 microSD 카드 (32GB 이상)
- **네트워크**: 이더넷 또는 Wi-Fi

### 최소 사양
- **모델**: Raspberry Pi 3 Model B+
- **RAM**: 1GB 이상
- **저장소**: 16GB microSD 카드

## 운영 체제 설정

### Raspberry Pi OS 설치

1. **Raspberry Pi Imager 사용**
   ```bash
   # Raspberry Pi Imager 다운로드
   https://www.raspberrypi.org/software/
   
   # SSH 활성화 (헤드리스 설치시)
   # boot 파티션에 ssh 파일 생성
   touch /boot/ssh
   ```

2. **초기 설정**
   ```bash
   # 시스템 업데이트
   sudo apt update && sudo apt upgrade -y
   
   # 기본 패키지 설치
   sudo apt install -y git python3 python3-pip docker.io docker-compose
   
   # 사용자를 docker 그룹에 추가
   sudo usermod -aG docker $USER
   ```

### 네트워크 설정

#### 이더넷 (권장)
```bash
# 고정 IP 설정 (선택사항)
sudo nano /etc/dhcpcd.conf

# 다음 내용 추가
interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 8.8.4.4
```

#### Wi-Fi 설정
```bash
# Wi-Fi 설정
sudo raspi-config
# Network Options → Wi-Fi → 네트워크 이름과 비밀번호 입력
```

## Python 환경 설정

### Python 버전 확인 및 업그레이드
```bash
# Python 버전 확인
python3 --version

# pip 업그레이드
python3 -m pip install --upgrade pip

# 필요한 시스템 패키지 설치
sudo apt install -y python3-dev python3-venv build-essential
```

### 가상 환경 설정
```bash
# 가상 환경 생성
python3 -m venv lora_gateway_env

# 가상 환경 활성화
source lora_gateway_env/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

## Docker 환경 설정

### Docker 설치 및 설정
```bash
# Docker 설치 (이미 설치된 경우 생략)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker Compose 설치
sudo apt install -y docker-compose

# Docker 서비스 시작
sudo systemctl enable docker
sudo systemctl start docker
```

### Docker 이미지 빌드
```bash
# 프로젝트 디렉터리에서 실행
cd /home/pi/lora_gateway_logger

# Docker 이미지 빌드
docker build -t lora-gateway-logger .

# Docker Compose로 실행
docker-compose -f docker-compose.test.yml up -d
```

## 시스템 리소스 최적화

### 메모리 사용량 최적화
```bash
# GPU 메모리 분할 최소화 (헤드리스 환경)
sudo raspi-config
# Advanced Options → Memory Split → 16

# 또는 직접 수정
echo "gpu_mem=16" | sudo tee -a /boot/config.txt
```

### 스왑 설정
```bash
# 스왑 크기 확인
free -h

# 스왑 크기 조정 (필요시)
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=100/CONF_SWAPSIZE=512/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### CPU 온도 모니터링
```bash
# CPU 온도 확인
vcgencmd measure_temp

# 지속적인 모니터링
watch -n 2 vcgencmd measure_temp
```

## 서비스 등록

### systemd 서비스 생성
```bash
# 서비스 파일 생성
sudo nano /etc/systemd/system/lora-gateway-logger.service
```

```ini
[Unit]
Description=LoRa Gateway Logger
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/lora_gateway_logger
Environment=PATH=/home/pi/lora_gateway_logger/lora_gateway_env/bin
ExecStart=/home/pi/lora_gateway_logger/lora_gateway_env/bin/python main.py
Restart=always
RestartSec=10

# 환경 변수
Environment=MQTT_BROKER_HOST=localhost
Environment=MQTT_BROKER_PORT=1883
Environment=DATABASE_PATH=/home/pi/lora_gateway_logger/lora_gateway.db
Environment=LOG_FILE=/home/pi/lora_gateway_logger/logs/lora_gateway.log

[Install]
WantedBy=multi-user.target
```

### 서비스 관리
```bash
# 서비스 등록
sudo systemctl daemon-reload
sudo systemctl enable lora-gateway-logger

# 서비스 시작/중지/재시작
sudo systemctl start lora-gateway-logger
sudo systemctl stop lora-gateway-logger
sudo systemctl restart lora-gateway-logger

# 서비스 상태 확인
sudo systemctl status lora-gateway-logger

# 로그 확인
journalctl -u lora-gateway-logger -f
```

## 로그 관리

### 로그 디렉터리 설정
```bash
# 로그 디렉터리 생성
mkdir -p /home/pi/lora_gateway_logger/logs

# 로그 파일 권한 설정
chmod 755 /home/pi/lora_gateway_logger/logs
```

### 로그 로테이션 설정
```bash
# logrotate 설정 파일 생성
sudo nano /etc/logrotate.d/lora-gateway-logger
```

```
/home/pi/lora_gateway_logger/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 pi pi
    postrotate
        systemctl reload lora-gateway-logger
    endscript
}
```

## 보안 설정

### 방화벽 설정
```bash
# UFW 설치 및 활성화
sudo apt install -y ufw
sudo ufw enable

# SSH 허용 (원격 관리용)
sudo ufw allow ssh

# MQTT 포트 허용 (필요시)
sudo ufw allow 1883/tcp

# 웹 애플리케이션 포트 허용 (Chirpstack 충돌 방지로 8081 사용)
sudo ufw allow 8081/tcp

# Chirpstack 포트 (기본 설치됨)
sudo ufw allow 8080/tcp
```

### SSH 보안 강화
```bash
# SSH 키 기반 인증 설정
ssh-keygen -t rsa -b 4096

# 비밀번호 인증 비활성화 (선택사항)
sudo nano /etc/ssh/sshd_config
# PasswordAuthentication no

sudo systemctl restart ssh
```

## 하드웨어 인터페이스

### GPIO 핀 사용 (필요시)
```bash
# GPIO 라이브러리 설치
pip install RPi.GPIO gpiozero

# I2C/SPI 활성화
sudo raspi-config
# Interfacing Options → I2C/SPI → Enable
```

### USB 포트 관리
```bash
# USB 디바이스 확인
lsusb

# USB 포트별 전력 관리
echo '1-1' | sudo tee /sys/bus/usb/drivers/usb/unbind
echo '1-1' | sudo tee /sys/bus/usb/drivers/usb/bind
```

## 모니터링 및 유지보수

### 시스템 상태 모니터링
```bash
# 시스템 리소스 확인
htop

# 디스크 사용량 확인
df -h

# 메모리 사용량 확인
free -h

# 네트워크 연결 확인
ip addr show
```

### 자동 업데이트 설정
```bash
# 자동 업데이트 패키지 설치
sudo apt install -y unattended-upgrades

# 자동 업데이트 설정
sudo dpkg-reconfigure unattended-upgrades
```

### 백업 스크립트
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/home/pi/backups"
PROJECT_DIR="/home/pi/lora_gateway_logger"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 데이터베이스 백업
cp $PROJECT_DIR/lora_gateway.db $BACKUP_DIR/lora_gateway_$DATE.db

# 설정 파일 백업
tar -czf $BACKUP_DIR/config_$DATE.tar.gz $PROJECT_DIR/*.py $PROJECT_DIR/requirements.txt

# 로그 아카이브
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz $PROJECT_DIR/logs/

# 오래된 백업 삭제 (30일 이상)
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "백업 완료: $DATE"
```

### cron 작업 설정
```bash
# crontab 편집
crontab -e

# 매일 새벽 2시에 백업 실행
0 2 * * * /home/pi/lora_gateway_logger/backup.sh

# 매 시간마다 시스템 상태 로깅
0 * * * * echo "$(date): $(vcgencmd measure_temp), $(free -h | grep Mem)" >> /home/pi/system_status.log
```

## 성능 최적화

### Python 애플리케이션 최적화
```python
# config.py에 라즈베리파이 최적화 설정 추가
@dataclass
class AppConfig:
    # ... 기존 설정 ...
    
    # 라즈베리파이 최적화
    stats_interval: int = 600  # 10분마다 통계 출력 (리소스 절약)
    max_memory_usage: int = 100 * 1024 * 1024  # 100MB 메모리 제한
```

### 데이터베이스 최적화
```bash
# SQLite 최적화
sqlite3 lora_gateway.db "PRAGMA optimize;"
sqlite3 lora_gateway.db "VACUUM;"
```

## 문제 해결

### 일반적인 문제와 해결방법

1. **MQTT 연결 실패**
   ```bash
   # 네트워크 연결 확인
   ping mqtt-broker-host
   
   # 포트 연결 확인
   telnet mqtt-broker-host 1883
   ```

2. **메모리 부족**
   ```bash
   # 메모리 사용량 확인
   free -h
   
   # 스왑 추가
   sudo fallocate -l 1G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

3. **SD 카드 성능 저하**
   ```bash
   # 읽기/쓰기 속도 테스트
   sudo hdparm -t /dev/mmcblk0
   
   # 파일 시스템 검사
   sudo fsck /dev/mmcblk0p2
   ```

4. **온도 과열**
   ```bash
   # CPU 주파수 제한 확인
   cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq
   
   # 쿨링 팬 설치 또는 방열판 추가 권장
   ```

## 원격 관리

### VNC 설정 (GUI 필요시)
```bash
# VNC 활성화
sudo raspi-config
# Interfacing Options → VNC → Enable

# VNC 서버 시작
sudo systemctl enable vncserver-x11-serviced
sudo systemctl start vncserver-x11-serviced
```

### 원격 모니터링
```bash
# SSH 터널링을 통한 안전한 연결
# Chirpstack 접근
ssh -L 8080:localhost:8080 pi@raspberry-pi-ip

# 웹 애플리케이션 접근 (8081 포트)
ssh -L 8081:localhost:8081 pi@raspberry-pi-ip

# 웹 기반 모니터링 도구 설치 (선택사항)
sudo apt install -y netdata
```

### RAK7248 특별 고려사항

RAK7248에서는 다음 서비스들이 기본적으로 실행됩니다:

| 포트 | 서비스 | 설명 |
|------|--------|------|
| 8080 | **Chirpstack** | LoRaWAN 네트워크 서버 웹 UI |
| 1883 | MQTT Broker | Chirpstack 내장 MQTT |
| 1700 | Packet Forwarder | LoRa 패킷 포워더 (UDP) |
| 22 | SSH | 원격 접속 |

따라서 웹 애플리케이션은 **8081 포트**를 사용해야 합니다.