# LoRa Gateway Logger - 개발 및 배포 가이드

**개발 환경**: PC (Windows)  
**실행 환경**: 라즈베리파이 RAK7248

---

## 🖥️ **PC에서 개발 및 테스트**

### 1. 단위 테스트 실행

```bash
# PC에서 실행
python -m pytest test_lora_gateway.py -v
```

### 2. 통합 테스트 실행

```bash
# PC에서 Docker MQTT 브로커 시작
docker run -d --name test-mosquitto -p 1883:1883 eclipse-mosquitto:2.0

# PC에서 통합 테스트 실행
python test_integration.py
```

### 3. Mock 데이터 테스트

```bash
# PC에서 실행 (Docker 브로커 필요)
python mock_mqtt_publisher.py --count 10 --interval 2
```

---

## 🔗 **PC → 라즈베리파이 배포 설정**

### 1. SSH 키 설정 (최초 1회만)

**PC에서** Git Bash 또는 WSL 사용:

```bash
# 1. PC에서 SSH 키 생성
ssh-keygen -t rsa -b 4096
# Enter로 기본 경로 사용, passphrase는 선택사항

# 2. PC에서 라즈베리파이로 공개키 복사
ssh-copy-id pi@192.168.0.110
# "yes" 입력 후 라즈베리파이 패스워드 입력

# 3. PC에서 연결 테스트
ssh pi@192.168.0.110
# passphrase 입력 후 연결되면 성공!
exit
```

### 2. 배포 파일 준비

**PC 프로젝트 폴더에서** 다음 파일들 생성:

```bash
# requirements.txt 생성
echo "paho-mqtt>=1.6.0" > requirements.txt
```

---

## 🚀 **배포 실행**

### 방법 1: 자동 배포 (권장)

**PC에서** 배포 스크립트 생성 후 실행:

```bash
# 1. PC에서 배포 스크립트 생성 (아래 스크립트 내용 복사)
# 2. PC에서 실행 권한 부여
chmod +x deploy.sh

# 3. PC에서 배포 실행
./deploy.sh 192.168.0.110 pi
```

### 방법 2: 수동 배포

**PC에서** 파일 전송:
```bash
# 파일 동기화
rsync -avz --exclude='*.log' --exclude='__pycache__' ./ pi@192.168.0.110:~/lora_gateway_logger/
```

**라즈베리파이에서** 설정:
```bash
# 1. PC에서 라즈베리파이에 SSH 접속
ssh pi@192.168.0.110

# 2. 라즈베리파이에서 의존성 설치
cd ~/lora_gateway_logger
pip3 install -r requirements.txt

# 3. 라즈베리파이에서 직접 실행
python3 main.py
```

---

## 🔧 **라즈베리파이에서 서비스 설정**

### 1. 시스템 서비스로 등록

**라즈베리파이에서** 실행:

```bash
# 1. 서비스 파일 생성
sudo nano /etc/systemd/system/lora-gateway-logger.service

# 2. 다음 내용 입력:
[Unit]
Description=LoRa Gateway Logger Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/lora_gateway_logger
ExecStart=/usr/bin/python3 /home/pi/lora_gateway_logger/main.py
Restart=always
RestartSec=10
Environment=MQTT_BROKER_HOST=localhost
Environment=MQTT_BROKER_PORT=1883
Environment=LOG_LEVEL=INFO

[Install]
WantedBy=multi-user.target

# 3. 서비스 등록 및 시작
sudo systemctl daemon-reload
sudo systemctl enable lora-gateway-logger.service
sudo systemctl start lora-gateway-logger.service
```

### 2. 서비스 관리

**라즈베리파이에서** 또는 **PC에서 SSH로**:

```bash
# 서비스 상태 확인
sudo systemctl status lora-gateway-logger.service

# 서비스 시작/중지/재시작
sudo systemctl start lora-gateway-logger.service
sudo systemctl stop lora-gateway-logger.service
sudo systemctl restart lora-gateway-logger.service

# 실시간 로그 확인  
sudo journalctl -u lora-gateway-logger.service -f
```

---

## 📊 **모니터링 및 디버깅**

### PC에서 원격 모니터링

```bash
# PC에서 라즈베리파이 상태 확인
ssh pi@192.168.0.110 'sudo systemctl status lora-gateway-logger.service'

# PC에서 라즈베리파이 로그 확인
ssh pi@192.168.0.110 'sudo journalctl -u lora-gateway-logger.service -f'

# PC에서 라즈베리파이 파일 확인
ssh pi@192.168.0.110 'ls -la ~/lora_gateway_logger/'
```

### 라즈베리파이에서 직접 확인

```bash
# 생성된 로그 파일들
ls -la ~/lora_gateway_logger/*.log
ls -la ~/lora_gateway_logger/uplink_data_*.json

# 실시간 애플리케이션 로그
tail -f ~/lora_gateway_logger/lora_gateway.log
```

## 🔍 원격 디버깅

### 1. 실시간 로그 모니터링

```bash
# systemd 로그 실시간 확인
python debug_tools.py tail-logs --host 192.168.1.100

# 또는 직접 SSH
ssh pi@192.168.1.100 'sudo journalctl -u lora-gateway-logger.service -f'
```

### 2. 시스템 상태 확인

```bash
# 전체 상태 확인
python debug_tools.py status --host 192.168.1.100

# 서비스 상태만 확인
python debug_tools.py service --host 192.168.1.100 --action status
```

### 3. 로그 파일 수집

```bash
# 원격 로그 파일들을 로컬로 수집
python debug_tools.py collect-logs --host 192.168.1.100

# 수집된 파일 분석
python debug_tools.py analyze --file ./remote_logs/uplink_data_20240101.json
```

### 4. 원격 테스트 데이터 전송

```bash
# 라즈베리파이에서 테스트 데이터 생성
python debug_tools.py test-data --host 192.168.1.100 --count 10
```

## 🛠️ 서비스 제어

### systemd 서비스 명령어

```bash
# 서비스 시작
python debug_tools.py service --host 192.168.1.100 --action start

# 서비스 중지
python debug_tools.py service --host 192.168.1.100 --action stop

# 서비스 재시작
python debug_tools.py service --host 192.168.1.100 --action restart

# 서비스 상태 확인
python debug_tools.py service --host 192.168.1.100 --action status
```

## 📊 로깅 및 모니터링

### 1. 로그 레벨 설정

```bash
# 환경변수로 로그 레벨 설정
export LOG_LEVEL=DEBUG
python main.py

# 또는 라즈베리파이 서비스 환경변수 수정
ssh pi@192.168.1.100
sudo systemctl edit lora-gateway-logger.service
# 다음 내용 추가:
# [Service]
# Environment=LOG_LEVEL=DEBUG
```

### 2. 원격 syslog 설정 (선택사항)

PC에서 syslog 서버 실행:
```bash
# rsyslog 설정 (Ubuntu/Debian)
sudo nano /etc/rsyslog.conf
# 다음 라인 주석 해제:
# $ModLoad imudp
# $UDPServerRun 514
# $UDPServerAddress 0.0.0.0

sudo systemctl restart rsyslog
```

라즈베리파이에서 환경변수 설정:
```bash
export SYSLOG_HOST=192.168.1.50  # PC IP
export SYSLOG_PORT=514
```

### 3. 통계 정보 확인

프로그램이 5분마다 자동으로 통계를 출력합니다:
- 가동시간
- 수신된 메시지 수
- 처리된 메시지 수  
- 오류 발생 수

## 🚨 문제 해결

### 일반적인 문제들

1. **MQTT 연결 실패**
   ```bash
   # 브로커 상태 확인
   telnet localhost 1883
   
   # 방화벽 확인
   sudo ufw status
   ```

2. **Permission 오류**
   ```bash
   # 로그 디렉토리 권한 설정
   sudo chown -R pi:pi /home/pi/lora_gateway_logger
   chmod +w /home/pi/lora_gateway_logger
   ```

3. **메모리/디스크 부족**
   ```bash
   # 시스템 리소스 확인
   python debug_tools.py status --host 192.168.1.100
   
   # 로그 파일 정리
   find . -name "*.log.*" -mtime +7 -delete
   ```

4. **네트워크 문제**
   ```bash
   # 네트워크 연결 테스트
   ping 192.168.1.100
   
   # SSH 연결 테스트  
   ssh -v pi@192.168.1.100
   ```

### 로그 파일 위치

- **라즈베리파이**: `/home/pi/lora_gateway_logger/`
  - `lora_gateway.log` - 애플리케이션 로그
  - `uplink_data_YYYYMMDD.json` - LoRa 데이터
- **systemd 로그**: `sudo journalctl -u lora-gateway-logger.service`

## 📁 파일 구조

```
lora_gateway_logger/
├── main.py                 # 메인 애플리케이션
├── test_lora_gateway.py    # 단위 테스트
├── test_integration.py     # 통합 테스트
├── mock_mqtt_publisher.py  # MQTT 모킹 도구
├── debug_tools.py          # 디버깅 유틸리티
├── deploy.sh              # 배포 스크립트
├── docker-compose.test.yml # 테스트용 Docker 구성
├── Dockerfile             # Docker 이미지
├── mosquitto.conf         # MQTT 브로커 설정
├── requirements.txt       # Python 패키지
└── README_TESTING.md      # 이 파일
```