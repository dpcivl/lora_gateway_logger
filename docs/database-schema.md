# 데이터베이스 스키마 문서

## 개요

LoRa Gateway Logger는 SQLite 데이터베이스를 사용하여 업링크 메시지와 JOIN 이벤트를 저장합니다.

## 테이블 구조

### 1. uplink_messages 테이블

업링크 메시지 데이터를 저장하는 테이블입니다.

```sql
CREATE TABLE uplink_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    application_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    dev_eui TEXT,
    
    -- 페이로드 데이터
    payload_base64 TEXT,
    payload_hex TEXT,
    payload_text TEXT,
    payload_size INTEGER,
    
    -- 네트워크 정보
    frame_count INTEGER,
    f_port INTEGER,
    frequency INTEGER,
    data_rate INTEGER,
    
    -- 신호 품질
    rssi REAL,
    snr REAL,
    
    -- 위치 정보
    latitude REAL,
    longitude REAL,
    
    -- 메타데이터
    hostname TEXT,
    raw_topic TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 필드 설명

| 필드명 | 타입 | 설명 |
|--------|------|------|
| id | INTEGER | 기본키 (자동증가) |
| timestamp | DATETIME | 메시지 수신 시간 |
| application_id | TEXT | LoRaWAN 애플리케이션 ID |
| device_id | TEXT | 디바이스 ID |
| dev_eui | TEXT | 디바이스 EUI |
| payload_base64 | TEXT | Base64 인코딩된 페이로드 |
| payload_hex | TEXT | HEX 형태의 페이로드 |
| payload_text | TEXT | 텍스트 형태의 페이로드 |
| payload_size | INTEGER | 페이로드 크기 (바이트) |
| frame_count | INTEGER | 프레임 카운터 |
| f_port | INTEGER | LoRaWAN 포트 번호 |
| frequency | INTEGER | 전송 주파수 (Hz) |
| data_rate | INTEGER | 데이터 전송률 |
| rssi | REAL | 수신 신호 강도 (dBm) |
| snr | REAL | 신호 대 잡음비 (dB) |
| latitude | REAL | 위도 |
| longitude | REAL | 경도 |
| hostname | TEXT | 수신 호스트명 |
| raw_topic | TEXT | MQTT 원본 토픽 |
| created_at | DATETIME | 레코드 생성 시간 |

### 2. join_events 테이블

디바이스 JOIN 이벤트를 저장하는 테이블입니다.

```sql
CREATE TABLE join_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    application_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    dev_eui TEXT NOT NULL,
    
    -- JOIN 관련 정보
    join_eui TEXT,
    dev_addr TEXT,
    
    -- 네트워크 정보
    frequency INTEGER,
    data_rate INTEGER,
    
    -- 신호 품질
    rssi REAL,
    snr REAL,
    
    -- 위치 정보
    latitude REAL,
    longitude REAL,
    
    -- 메타데이터
    hostname TEXT,
    raw_topic TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 필드 설명

| 필드명 | 타입 | 설명 |
|--------|------|------|
| id | INTEGER | 기본키 (자동증가) |
| timestamp | DATETIME | JOIN 이벤트 발생 시간 |
| application_id | TEXT | LoRaWAN 애플리케이션 ID |
| device_id | TEXT | 디바이스 ID |
| dev_eui | TEXT | 디바이스 EUI |
| join_eui | TEXT | JOIN EUI (AppEUI) |
| dev_addr | TEXT | 할당된 디바이스 주소 |
| frequency | INTEGER | 전송 주파수 (Hz) |
| data_rate | INTEGER | 데이터 전송률 |
| rssi | REAL | 수신 신호 강도 (dBm) |
| snr | REAL | 신호 대 잡음비 (dB) |
| latitude | REAL | 위도 |
| longitude | REAL | 경도 |
| hostname | TEXT | 수신 호스트명 |
| raw_topic | TEXT | MQTT 원본 토픽 |
| created_at | DATETIME | 레코드 생성 시간 |

## 인덱스

성능 최적화를 위해 다음 인덱스들이 생성됩니다:

### uplink_messages 테이블 인덱스
- `idx_device_timestamp`: device_id, timestamp
- `idx_application_timestamp`: application_id, timestamp
- `idx_timestamp`: timestamp

### join_events 테이블 인덱스
- `idx_join_device_timestamp`: device_id, timestamp
- `idx_join_timestamp`: timestamp
- `idx_join_dev_eui`: dev_eui

## 주요 쿼리 예시

### 최근 메시지 조회
```sql
SELECT * FROM uplink_messages 
ORDER BY timestamp DESC 
LIMIT 100;
```

### 특정 디바이스 메시지 조회
```sql
SELECT * FROM uplink_messages 
WHERE device_id = 'your_device_id'
ORDER BY timestamp DESC 
LIMIT 100;
```

### 통계 정보 조회
```sql
SELECT 
    COUNT(*) as total_messages,
    COUNT(DISTINCT device_id) as unique_devices,
    COUNT(DISTINCT application_id) as unique_applications,
    MIN(timestamp) as first_message,
    MAX(timestamp) as last_message
FROM uplink_messages;
```

## 데이터 모델

데이터베이스 스키마는 다음 Python 모델과 연동됩니다:
- `UplinkMessage` 클래스 (models.py)
- `JoinEvent` 클래스 (models.py)

상세한 데이터 모델 정보는 `models.py` 파일을 참조하세요.