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
(git bash에서 실행하는 것을 권장)

```bash
# 1. PC에서 배포 스크립트 생성 (아래 스크립트 내용 복사)
# 2. PC에서 실행 권한 부여
chmod +x deploy.sh

# 3. PC에서 배포 실행
./deploy.sh 192.168.0.110 pi
```

### 방법 2: 수동 배포

**PC에서** 파일 전송 (Git Bash):
```bash
# 1. 라즈베리파이에 디렉토리 생성  
ssh pi@192.168.0.110 "mkdir -p ~/lora_gateway_logger"

# 2. 파일 전송 (scp 사용 - Windows Git Bash 호환)
scp main.py requirements.txt pi@192.168.0.110:~/lora_gateway_logger/

# 또는 rsync가 설치된 경우 (WSL 등)
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

---

## 🚨 **문제 해결**

### SSH 연결 문제
```bash
# PC에서 연결 테스트
ssh -v pi@192.168.0.110

# 라즈베리파이에서 SSH 서비스 확인
sudo systemctl status ssh
```

### MQTT 연결 문제
```bash
# 라즈베리파이에서 브로커 상태 확인
telnet localhost 1883

# 라즈베리파이에서 방화벽 확인
sudo ufw status
```

### 권한 문제
```bash
# 라즈베리파이에서 디렉토리 권한 설정
sudo chown -R pi:pi /home/pi/lora_gateway_logger
chmod +w /home/pi/lora_gateway_logger
```

---

## 📋 **요약: 키 설정부터 배포까지**

1. **PC에서** SSH 키 생성 및 복사 ✅ (완료)
2. **PC에서** `requirements.txt` 생성 ✅ (완료)
3. **PC에서** 파일 전송 (scp 또는 배포 스크립트)
4. **라즈베리파이에서** 의존성 설치 및 실행
5. **라즈베리파이에서** 서비스 등록 (선택사항)

## 🚀 **간단 배포 명령어 (Git Bash)**

```bash
# 1. 디렉토리 생성
ssh pi@192.168.0.110 "mkdir -p ~/lora_gateway_logger"

# 2. 파일 전송
scp main.py requirements.txt pi@192.168.0.110:~/lora_gateway_logger/

# 3. 의존성 설치
ssh pi@192.168.0.110 "cd ~/lora_gateway_logger && pip3 install -r requirements.txt"

# 4. 프로그램 실행
ssh pi@192.168.0.110 "cd ~/lora_gateway_logger && python3 main.py"
```

**다음 단계**: 위의 명령어들을 Git Bash에서 순서대로 실행하면 됩니다!