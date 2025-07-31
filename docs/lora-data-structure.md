# LoRa 데이터 구조 문서

## 개요

LoRa Gateway Logger는 LoRaWAN 네트워크를 통해 전송되는 디바이스 데이터를 수신하고 처리합니다. 이 문서는 LoRa 데이터의 구조와 처리 방식을 설명합니다.

## MQTT 토픽 구조

### 업링크 메시지 토픽
```
application/{application_id}/device/{device_id}/event/up
```

### JOIN 이벤트 토픽
```
application/{application_id}/device/{device_id}/event/join
```

#### 토픽 파라미터
- `{application_id}`: LoRaWAN 애플리케이션 ID
- `{device_id}`: 디바이스 ID

## 업링크 메시지 구조

### JSON 페이로드 예시

```json
{
  "applicationID": "1",
  "applicationName": "test-app",
  "deviceName": "test-device",
  "devEUI": "1234567890abcdef",
  "rxInfo": [
    {
      "gatewayID": "gateway001",
      "rssi": -85,
      "loRaSNR": 7.5,
      "location": {
        "latitude": 37.5665,
        "longitude": 126.9780
      }
    }
  ],
  "txInfo": {
    "frequency": 868100000,
    "dr": 5
  },
  "adr": true,
  "fCnt": 123,
  "fPort": 1,
  "data": "SGVsbG8gV29ybGQ="
}
```

### 주요 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `devEUI` | string | 디바이스 EUI (64비트 고유 식별자) |
| `fCnt` | number | 프레임 카운터 (업링크 메시지 순서) |
| `fPort` | number | LoRaWAN 포트 번호 (1-223) |
| `data` | string | Base64 인코딩된 페이로드 데이터 |
| `rxInfo` | array | 수신 정보 (게이트웨이별) |
| `txInfo` | object | 전송 정보 |
| `adr` | boolean | Adaptive Data Rate 사용 여부 |

#### rxInfo 배열 구조
```json
{
  "gatewayID": "gateway001",
  "rssi": -85,
  "loRaSNR": 7.5,
  "location": {
    "latitude": 37.5665,
    "longitude": 126.9780
  }
}
```

- `rssi`: 수신 신호 강도 (dBm)
- `loRaSNR`: 신호 대 잡음비 (dB)
- `location`: 게이트웨이 위치 정보

#### txInfo 객체 구조
```json
{
  "frequency": 868100000,
  "dr": 5
}
```

- `frequency`: 전송 주파수 (Hz)
- `dr`: Data Rate Index (0-15)

## JOIN 이벤트 구조

### JSON 페이로드 예시

```json
{
  "applicationID": "1",
  "applicationName": "test-app",
  "deviceName": "test-device",
  "devEUI": "1234567890abcdef",
  "joinEUI": "0000000000000000",
  "devAddr": "01020304",
  "rxInfo": [
    {
      "gatewayID": "gateway001",
      "rssi": -82,
      "loRaSNR": 8.2,
      "location": {
        "latitude": 37.5665,
        "longitude": 126.9780
      }
    }
  ],
  "txInfo": {
    "frequency": 868100000,
    "dr": 0
  }
}
```

### JOIN 이벤트 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `devEUI` | string | 디바이스 EUI |
| `joinEUI` | string | JOIN EUI (구 AppEUI) |
| `devAddr` | string | 할당된 디바이스 주소 (32비트) |
| `rxInfo` | array | 수신 정보 |
| `txInfo` | object | 전송 정보 |

## 페이로드 데이터 처리

### Base64 디코딩 과정

1. **Base64 디코딩**: `SGVsbG8gV29ybGQ=` → 바이트 배열
2. **HEX 변환**: `48656C6C6F20576F726C64`
3. **텍스트 변환**: `Hello World` (UTF-8 가능한 경우)

### 코드 예시

```python
import base64

# Base64 페이로드
payload_b64 = "SGVsbG8gV29ybGQ="

# 디코딩
decoded_bytes = base64.b64decode(payload_b64)
hex_string = decoded_bytes.hex().upper()
text_string = decoded_bytes.decode('utf-8')

print(f"HEX: {hex_string}")    # HEX: 48656C6C6F20576F726C64
print(f"Text: {text_string}")  # Text: Hello World
```

## 데이터 파싱 클래스

### LoRaMessageParser 사용법

```python
from core.message_parser import LoRaMessageParser

parser = LoRaMessageParser()

# 토픽 파싱
topic = "application/1/device/test-device/event/up"
app_id, dev_id, event_type = parser.parse_topic(topic)

# 페이로드 파싱
payload_bytes = b'{"devEUI":"1234567890abcdef","data":"SGVsbG8="}'
payload_dict = parser.parse_payload(payload_bytes)

# 업링크 정보 추출
if event_type == "up":
    summary = parser.extract_uplink_summary(payload_dict)
elif event_type == "join":
    summary = parser.extract_join_summary(payload_dict)
```

## 데이터 검증

### 필수 필드 검증

업링크 메시지 최소 요구사항:
- `devEUI`: 디바이스 식별을 위해 필수
- `fCnt`: 메시지 순서 확인
- `data`: 실제 페이로드 데이터

JOIN 이벤트 최소 요구사항:
- `devEUI`: 디바이스 식별
- `devAddr`: 할당된 주소 확인

### 데이터 타입 검증

```python
def validate_uplink_data(payload):
    """업링크 데이터 검증"""
    required_fields = ['devEUI', 'fCnt', 'data']
    
    for field in required_fields:
        if field not in payload:
            return False, f"Missing field: {field}"
    
    # fCnt는 숫자여야 함
    if not isinstance(payload['fCnt'], int):
        return False, "fCnt must be integer"
    
    # data는 Base64 형식이어야 함
    try:
        base64.b64decode(payload['data'])
    except:
        return False, "Invalid Base64 data"
    
    return True, "Valid"
```

## 신호 품질 해석

### RSSI (Received Signal Strength Indicator)
- 단위: dBm
- 범위: -120 dBm ~ 0 dBm
- 해석:
  - `-50 ~ -70 dBm`: 매우 강함
  - `-70 ~ -85 dBm`: 강함
  - `-85 ~ -100 dBm`: 보통
  - `-100 dBm 이하`: 약함

### SNR (Signal-to-Noise Ratio)
- 단위: dB
- 해석:
  - `10 dB 이상`: 매우 좋음
  - `5 ~ 10 dB`: 좋음
  - `0 ~ 5 dB`: 보통
  - `0 dB 이하`: 나쁨

## 데이터 전송률 (Data Rate)

### LoRaWAN Data Rate Index

| DR | SF | BW (kHz) | 비트레이트 (bps) |
|----|----|---------:|----------------:|
| 0  | 12 | 125      | 250             |
| 1  | 11 | 125      | 440             |
| 2  | 10 | 125      | 980             |
| 3  | 9  | 125      | 1760            |
| 4  | 8  | 125      | 3125            |
| 5  | 7  | 125      | 5470            |

- SF: Spreading Factor
- BW: Bandwidth

## 주파수 대역

### 지역별 주파수 계획

#### EU868 (유럽)
- 867.1 - 868.5 MHz
- 채널: 8개 (기본 3개 + 선택 5개)

#### US915 (북미)
- 902 - 928 MHz
- 채널: 72개 (64개 업링크 + 8개 다운링크)

#### AS923 (아시아)
- 920 - 925 MHz
- 채널: 8개

## 에러 처리

### 일반적인 에러 케이스

1. **토픽 형식 오류**
   ```
   잘못된 토픽: application/device/up
   올바른 토픽: application/1/device/test/event/up
   ```

2. **JSON 파싱 오류**
   ```json
   // 잘못된 JSON
   {"devEUI": "123", invalid}
   
   // 올바른 JSON
   {"devEUI": "123", "fCnt": 1}
   ```

3. **Base64 디코딩 오류**
   ```
   잘못된 Base64: "Invalid=Base64=="
   올바른 Base64: "SGVsbG8gV29ybGQ="
   ```

### 에러 로깅

```python
import logging

logger = logging.getLogger(__name__)

try:
    payload = parser.parse_payload(message)
except Exception as e:
    logger.error(f"페이로드 파싱 실패: {e}")
    logger.debug(f"원본 메시지: {message}")
```

## 웹 애플리케이션에서 활용

### JavaScript에서 데이터 처리

```javascript
// 업링크 메시지 처리
function processUplinkMessage(message) {
    const {
        deviceId,
        timestamp,
        rssi,
        snr,
        payloadText,
        frameCount
    } = message;
    
    // 신호 품질 평가
    const signalQuality = evaluateSignalQuality(rssi, snr);
    
    // UI 업데이트
    updateDeviceStatus(deviceId, {
        lastSeen: timestamp,
        signalQuality: signalQuality,
        message: payloadText,
        frameCount: frameCount
    });
}

function evaluateSignalQuality(rssi, snr) {
    if (rssi > -70 && snr > 10) return 'excellent';
    if (rssi > -85 && snr > 5) return 'good';
    if (rssi > -100 && snr > 0) return 'fair';
    return 'poor';
}
```

### Java에서 데이터 처리

```java
@Entity
public class UplinkMessage {
    private String deviceEui;
    private Integer frameCount;
    private String payloadBase64;
    private Float rssi;
    private Float snr;
    
    public String decodePayload() {
        try {
            byte[] decoded = Base64.getDecoder().decode(payloadBase64);
            return new String(decoded, StandardCharsets.UTF_8);
        } catch (Exception e) {
            return "[디코딩 실패]";
        }
    }
    
    public SignalQuality getSignalQuality() {
        if (rssi > -70 && snr > 10) return SignalQuality.EXCELLENT;
        if (rssi > -85 && snr > 5) return SignalQuality.GOOD;
        if (rssi > -100 && snr > 0) return SignalQuality.FAIR;
        return SignalQuality.POOR;
    }
}
```