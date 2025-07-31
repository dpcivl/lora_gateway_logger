# 프로젝트 구조 문서

## 개요

LoRa Gateway Logger는 LoRaWAN 디바이스로부터 전송되는 데이터를 MQTT를 통해 수신하고, SQLite 데이터베이스에 저장하는 Python 애플리케이션입니다.

## 디렉터리 구조

```
lora_gateway_logger/
├── core/                      # 핵심 모듈
│   ├── __init__.py
│   ├── data_processor.py      # 데이터 처리 로직
│   ├── message_parser.py      # 메시지 파싱 로직
│   └── mqtt_client.py         # MQTT 클라이언트
├── docs/                      # 문서
│   ├── database-schema.md     # DB 스키마 정보
│   ├── database-connection.md # DB 연결 정보
│   ├── port-configuration.md  # 포트 설정
│   ├── lora-data-structure.md # LoRa 데이터 구조
│   ├── raspberry-pi-environment.md # 라즈베리파이 환경
│   └── project-structure.md   # 이 문서
├── config.py                  # 설정 관리
├── database.py                # 데이터베이스 모듈
├── main.py                    # 메인 애플리케이션
├── models.py                  # 데이터 모델
├── requirements.txt           # Python 의존성
├── Dockerfile                 # Docker 이미지 빌드
├── docker-compose.test.yml    # Docker Compose 설정
├── mosquitto.conf             # MQTT 브로커 설정
├── deploy.sh                  # 배포 스크립트
├── deploy_with_agent.sh       # 에이전트 포함 배포
├── mock_mqtt_publisher.py     # 테스트용 MQTT 퍼블리셔
├── test_*.py                  # 단위 테스트 파일들
├── README.md                  # 프로젝트 설명
└── README_TESTING.md          # 테스트 가이드
```

## 핵심 모듈 설명

### 1. main.py
애플리케이션의 진입점입니다.

**주요 기능:**
- 설정 로드 및 로깅 초기화
- LoRaGatewayLogger 인스턴스 생성 및 실행
- 시그널 처리 (SIGINT)

**주요 클래스:**
- `LoRaGatewayLogger`: 메인 애플리케이션 클래스

### 2. config.py
환경 변수 기반 설정 관리 모듈입니다.

**주요 클래스:**
- `MQTTConfig`: MQTT 브로커 설정
- `DatabaseConfig`: 데이터베이스 설정
- `LoggingConfig`: 로깅 설정
- `AppConfig`: 전체 애플리케이션 설정

**주요 함수:**
- `load_config_from_env()`: 환경 변수에서 설정 로드
- `setup_logging()`: 로깅 시스템 초기화

### 3. models.py
데이터 모델 정의 모듈입니다.

**주요 클래스:**
- `UplinkMessage`: 업링크 메시지 데이터 클래스
- `JoinEvent`: JOIN 이벤트 데이터 클래스

**주요 메서드:**
- `to_dict()`: 딕셔너리 변환 (JSON 직렬화용)
- `from_payload_summary()`: 페이로드에서 객체 생성

### 4. database.py
SQLite 데이터베이스 관리 모듈입니다.

**주요 클래스:**
- `LoRaDatabase`: SQLite 데이터베이스 관리

**주요 메서드:**
- `insert_uplink_message()`: 업링크 메시지 저장
- `insert_join_event()`: JOIN 이벤트 저장
- `get_recent_messages()`: 최근 메시지 조회
- `get_statistics()`: 통계 정보 조회

## Core 모듈 상세

### 1. core/mqtt_client.py
MQTT 클라이언트 관리 모듈입니다.

**주요 클래스:**
- `LoRaMQTTClient`: MQTT 클라이언트 래퍼

**주요 메서드:**
- `connect()`: MQTT 브로커 연결
- `set_message_callback()`: 메시지 콜백 설정
- `start_loop()`: 메시지 수신 루프 시작

### 2. core/message_parser.py
LoRa 메시지 파싱 모듈입니다.

**주요 클래스:**
- `LoRaMessageParser`: 메시지 파싱 로직

**주요 메서드:**
- `parse_topic()`: MQTT 토픽 파싱
- `parse_payload()`: JSON 페이로드 파싱
- `extract_uplink_summary()`: 업링크 정보 추출
- `extract_join_summary()`: JOIN 정보 추출

### 3. core/data_processor.py
데이터 처리 및 저장 모듈입니다.

**주요 클래스:**
- `LoRaDataProcessor`: 데이터 처리 로직

**주요 메서드:**
- `process_uplink_message()`: 업링크 메시지 처리
- `process_join_event()`: JOIN 이벤트 처리
- `get_statistics()`: 처리 통계 조회

## 설정 파일

### 환경 변수
애플리케이션은 다음 환경 변수들을 사용합니다:

```bash
# MQTT 설정
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_USERNAME=username
MQTT_PASSWORD=password
MQTT_CONNECTION_RETRIES=3
MQTT_CONNECTION_TIMEOUT=60

# 데이터베이스 설정
ENABLE_SQLITE=true
DATABASE_PATH=lora_gateway.db

# 로깅 설정
LOG_LEVEL=INFO
LOG_FILE=lora_gateway.log
LOG_MAX_SIZE=10485760
LOG_BACKUP_COUNT=5
SYSLOG_HOST=remote-server
SYSLOG_PORT=514

# 애플리케이션 설정
STATS_INTERVAL=300
```

## 테스트 구조

### 단위 테스트 파일

1. **test_lora_gateway.py**
   - 메인 애플리케이션 로직 테스트
   - MQTT 메시지 처리 테스트

2. **test_sqlite.py**
   - SQLite 데이터베이스 기능 테스트
   - CRUD 작업 테스트

3. **test_integration.py**
   - 통합 테스트
   - 전체 워크플로우 테스트

4. **test_refactored.py**
   - 리팩토링 후 회귀 테스트

### 테스트 도구

- **mock_mqtt_publisher.py**: 테스트용 MQTT 메시지 발송 도구

## 배포 구조

### Docker 환경

1. **Dockerfile**
   ```dockerfile
   FROM python:3.9-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY main.py .
   COPY *.py .
   RUN mkdir -p /app/logs
   CMD ["python", "main.py"]
   ```

2. **docker-compose.test.yml**
   - MQTT 브로커 (Eclipse Mosquitto)
   - LoRa Gateway Logger 애플리케이션

### 배포 스크립트

1. **deploy.sh**: 기본 배포 스크립트
2. **deploy_with_agent.sh**: 에이전트 포함 배포

## 데이터 흐름

```
LoRa Device → LoRaWAN Gateway → MQTT Broker → LoRa Gateway Logger → SQLite Database
                                                      ↓
                                              JSON Files (백업)
```

### 상세 데이터 흐름

1. **메시지 수신**: MQTT 클라이언트가 브로커에서 메시지 수신
2. **토픽 파싱**: `application/{app_id}/device/{dev_id}/event/{event_type}` 형태 파싱
3. **페이로드 파싱**: JSON 형태의 메시지 본문 파싱
4. **데이터 추출**: 업링크/JOIN 이벤트별 주요 정보 추출
5. **모델 생성**: `UplinkMessage` 또는 `JoinEvent` 객체 생성
6. **데이터 저장**: SQLite 데이터베이스에 저장
7. **JSON 백업**: JSON 파일로 백업 저장 (선택사항)

## 로깅 시스템

### 로그 레벨
- `DEBUG`: 상세한 디버깅 정보
- `INFO`: 일반적인 정보 메시지
- `WARNING`: 경고 메시지
- `ERROR`: 오류 메시지

### 로그 출력 대상
1. **콘솔**: 표준 출력
2. **파일**: 로테이션 지원 파일 로깅
3. **Syslog**: 원격 로그 서버 (선택사항)

## 성능 고려사항

### 메모리 사용량
- SQLite 연결 풀링 없음 (단일 프로세스)
- 메시지별 객체 생성 최소화
- 통계 정보 주기적 출력 (메모리 누수 방지)

### 디스크 I/O
- SQLite WAL 모드 사용 (동시성 향상)
- 인덱스 최적화 (timestamp, device_id 기준)
- 로그 파일 로테이션

### 네트워크
- MQTT QoS 0 사용 (성능 우선)
- 연결 재시도 로직
- Keep-alive 설정

## 확장성 고려사항

### 수평 확장
- 다중 인스턴스 실행 가능 (디바이스/애플리케이션별 분리)
- MQTT 토픽 필터링을 통한 부하 분산

### 수직 확장
- 메모리 사용량 모니터링
- CPU 사용률 최적화
- 디스크 공간 관리

## 보안 고려사항

### 인증 및 권한
- MQTT 브로커 인증 (username/password)
- SSL/TLS 지원 (MQTTS)

### 데이터 보호
- SQLite 파일 권한 관리
- 로그 파일 보안
- 네트워크 트래픽 암호화

## 모니터링 포인트

### 애플리케이션 상태
- MQTT 연결 상태
- 메시지 처리율
- 오류 발생률
- 메모리/CPU 사용률

### 데이터 품질
- 메시지 손실률
- 파싱 오류율
- 데이터베이스 저장 성공률

### 시스템 리소스
- 디스크 사용량
- 네트워크 대역폭
- SQLite 성능 지표

## 문제 해결 가이드

### 일반적인 문제
1. **MQTT 연결 실패**: 브로커 설정 및 네트워크 확인
2. **메시지 파싱 오류**: 페이로드 형식 검증
3. **데이터베이스 오류**: SQLite 파일 권한 및 공간 확인
4. **메모리 누수**: 통계 정보 및 가비지 컬렉션 모니터링

### 로그 분석
- 오류 패턴 분석
- 성능 병목 지점 식별
- 트렌드 분석을 통한 용량 계획