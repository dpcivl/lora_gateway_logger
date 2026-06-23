<!--
  lora_gateway_logger 저장소의 기존 README.md 를 이 내용으로 교체하세요.
  [확인 필요] 표시된 부분은 실제 코드/환경에 맞게 채워주세요.
-->

# LoRa Gateway Logger

라즈베리파이 LoRa 게이트웨이(RAK7248)가 수신하는 MQTT 메시지를 수집해
SQLite 데이터베이스에 저장하는 Python 로거입니다.
[lora_web_dashboard](https://github.com/dpcivl/lora_web_dashboard)와 연동되어 수집된 데이터를 시각화합니다.

## 개요

LoRaWAN 게이트웨이는 디바이스 메시지를 MQTT 브로커로 발행합니다.
이 로거는 해당 브로커를 구독(subscribe)하여 수신 메시지를 파싱하고,
디바이스 정보·신호 품질(RSSI/SNR)·JOIN 이벤트 등을 SQLite에 기록합니다.

## 주요 기능

- MQTT 브로커 구독 및 실시간 메시지 수신
- LoRaWAN 메시지 파싱 (디바이스 ID, Frame Count, RSSI/SNR 등)
- SQLite 데이터베이스 저장
- 테스트용 Mock MQTT Publisher 제공 (`mock_mqtt_publisher.py`)
- Docker 기반 배포 (`deploy.sh`)

## 기술 스택

- **언어**: Python (3.11)
- **메시지 브로커**: MQTT (Mosquitto)
- **데이터베이스**: SQLite
- **컨테이너**: Docker
- **개발 환경**: Windows 11
- **타겟 환경**: 라즈베리파이 (RAK7248)

## 프로젝트 구조

```
lora_gateway_logger/
├── core/                  # 핵심 로직 모듈
├── main.py                # 진입점
├── config.py              # 설정
├── database.py            # DB 연결/쿼리
├── models.py              # 데이터 모델
├── mock_mqtt_publisher.py # 테스트용 MQTT 발행기
├── mosquitto.conf         # MQTT 브로커 설정
├── Dockerfile
├── deploy.sh              # 배포 스크립트
├── requirements.txt
└── test_*.py              # 단위/통합 테스트
```

## 시작하기

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 설정

`config.py`에서 MQTT 브로커 주소·토픽·DB 경로를 설정합니다.


### 3. 실행

```bash
python main.py
```

### Docker로 실행

```bash
./deploy.sh
```

## 테스트

```bash
# 단위 테스트
python -m pytest test_lora_gateway.py

# 통합 테스트 (Mock MQTT Publisher 사용)
python -m pytest test_integration.py
```

자세한 테스트 방법은 [README_TESTING.md](README_TESTING.md)를 참고하세요.

## 관련 프로젝트

- [lora_web_dashboard](https://github.com/dpcivl/lora_web_dashboard) — 수집된 데이터를 시각화하는 웹 대시보드
- [lora_tester](https://github.com/dpcivl/lora_tester) — LoRa 모듈 검증용 임베디드 테스트 도구

## 라이선스

[확인 필요: 예) MIT]
