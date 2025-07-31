# 포트 설정 문서

## 개요

LoRa Gateway Logger는 MQTT 브로커를 통해 LoRa 데이터를 수신하며, 웹 애플리케이션과의 연동을 위한 다양한 포트 설정이 필요합니다.

## MQTT 브로커 포트

### 기본 MQTT 포트

| 포트 | 프로토콜 | 설명 | 보안 |
|------|----------|------|------|
| 1883 | MQTT | 기본 MQTT 포트 | 비암호화 |
| 8883 | MQTTS | SSL/TLS 암호화 MQTT | 암호화 |
| 8080 | WebSocket | MQTT over WebSocket | 비암호화 |
| 8443 | WebSocket | MQTT over WebSocket (SSL) | 암호화 |

### 환경 변수 설정

```bash
# MQTT 브로커 호스트 및 포트
export MQTT_BROKER_HOST=localhost
export MQTT_BROKER_PORT=1883

# SSL 사용시
export MQTT_BROKER_PORT=8883

# 사용자 인증
export MQTT_USERNAME=your_username
export MQTT_PASSWORD=your_password
```

### config.py 설정

```python
@dataclass
class MQTTConfig:
    broker_host: str = "localhost"
    broker_port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    connection_retries: int = 3
    connection_timeout: int = 60
```

## 웹 애플리케이션 포트

### Java Spring Boot 애플리케이션

#### 개발 환경
```yaml
# application-dev.yml
server:
  port: 8080
  servlet:
    context-path: /api
```

#### 운영 환경
```yaml
# application-prod.yml
server:
  port: 8443
  ssl:
    enabled: true
    key-store: classpath:keystore.p12
    key-store-password: your_password
    key-store-type: PKCS12
```

### JavaScript/React 개발 서버
```json
{
  "scripts": {
    "dev": "react-scripts start",
    "build": "react-scripts build"
  },
  "proxy": "http://localhost:8080"
}
```

기본 개발 서버 포트: `3000`

## 포트 충돌 방지

### 포트 사용 확인
```bash
# Windows
netstat -an | findstr :1883
netstat -an | findstr :8080

# Linux/Mac
netstat -tuln | grep :1883
netstat -tuln | grep :8080
```

### 사용 가능한 포트 찾기
```bash
# Windows
netstat -an | findstr /v LISTENING

# Linux/Mac
netstat -tuln | grep -v LISTEN
```

## Docker 환경 포트 매핑

### docker-compose.yml 예시

```yaml
version: '3.8'

services:
  lora-gateway-logger:
    build: .
    ports:
      - "8080:8080"  # 웹 애플리케이션
    environment:
      - MQTT_BROKER_HOST=mosquitto
      - MQTT_BROKER_PORT=1883
    depends_on:
      - mosquitto
    
  mosquitto:
    image: eclipse-mosquitto:2.0
    ports:
      - "1883:1883"  # MQTT
      - "9001:9001"  # WebSocket
    volumes:
      - ./mosquitto.conf:/mosquitto/config/mosquitto.conf
    
  web-app:
    build: ./web
    ports:
      - "3000:3000"  # React 개발 서버
      - "8081:8080"  # Java 백엔드
    environment:
      - REACT_APP_API_URL=http://localhost:8081/api
```

### 포트 매핑 설명

| 호스트 포트 | 컨테이너 포트 | 서비스 | 설명 |
|-------------|---------------|--------|------|
| 1883 | 1883 | MQTT Broker | LoRa 데이터 수신 |
| 9001 | 9001 | MQTT WebSocket | 웹소켓 연결 |
| 3000 | 3000 | React Dev | 프론트엔드 개발 서버 |
| 8081 | 8080 | Spring Boot | Java 백엔드 API |

## 방화벽 설정

### Windows 방화벽
```powershell
# MQTT 포트 허용
netsh advfirewall firewall add rule name="MQTT" dir=in action=allow protocol=TCP localport=1883

# 웹 애플리케이션 포트 허용
netsh advfirewall firewall add rule name="WebApp" dir=in action=allow protocol=TCP localport=8080
```

### Linux iptables
```bash
# MQTT 포트 허용
sudo iptables -A INPUT -p tcp --dport 1883 -j ACCEPT

# 웹 애플리케이션 포트 허용
sudo iptables -A INPUT -p tcp --dport 8080 -j ACCEPT

# 설정 저장
sudo iptables-save > /etc/iptables/rules.v4
```

### UFW (Ubuntu)
```bash
# MQTT 포트 허용
sudo ufw allow 1883/tcp

# 웹 애플리케이션 포트 허용
sudo ufw allow 8080/tcp

# 방화벽 활성화
sudo ufw enable
```

## 라즈베리파이 특별 고려사항

### GPIO 포트와의 충돌 방지
라즈베리파이에서는 하드웨어 GPIO 포트와 네트워크 포트를 구분해야 합니다.

### 리소스 제한
```bash
# 사용 가능한 포트 범위 확인
cat /proc/sys/net/ipv4/ip_local_port_range

# 포트 사용량 확인
ss -tuln | wc -l
```

## 포트 테스트

### MQTT 연결 테스트
```bash
# mosquitto 클라이언트 사용
mosquitto_sub -h localhost -p 1883 -t "application/+/device/+/event/+"

# Python으로 테스트
python3 -c "
import paho.mqtt.client as mqtt
client = mqtt.Client()
client.connect('localhost', 1883, 60)
print('MQTT 연결 성공')
"
```

### 웹 애플리케이션 테스트
```bash
# HTTP 연결 테스트
curl -I http://localhost:8080/health

# HTTPS 연결 테스트
curl -k -I https://localhost:8443/health
```

## 환경별 포트 구성

### 개발 환경
```bash
# .env.development
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
WEB_SERVER_PORT=3000
API_SERVER_PORT=8080
```

### 테스트 환경
```bash
# .env.test
MQTT_BROKER_HOST=test-broker.local
MQTT_BROKER_PORT=1883
WEB_SERVER_PORT=3001
API_SERVER_PORT=8081
```

### 운영 환경
```bash
# .env.production
MQTT_BROKER_HOST=prod-broker.company.com
MQTT_BROKER_PORT=8883
WEB_SERVER_PORT=443
API_SERVER_PORT=8443
```

## 로드 밸런싱

### Nginx 설정 예시
```nginx
upstream api_servers {
    server localhost:8080;
    server localhost:8081;
    server localhost:8082;
}

server {
    listen 80;
    server_name your-domain.com;
    
    location /api {
        proxy_pass http://api_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 모니터링

### 포트 사용량 모니터링
```bash
# 포트별 연결 수 확인
netstat -an | awk '/LISTEN/ {print $4}' | cut -d: -f2 | sort | uniq -c

# 특정 포트 모니터링
watch -n 1 'netstat -an | grep :1883'
```

### 성능 모니터링
```bash
# 연결당 대역폭 사용량
iftop -i eth0 -P

# 포트별 트래픽
ss -i state connected '( dport = :1883 or sport = :1883 )'
```