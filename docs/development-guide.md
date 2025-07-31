# 개발 가이드

## 개요

이 문서는 LoRa Gateway Logger 프로젝트에 참여하는 개발자들을 위한 가이드입니다.

## 개발 환경 설정

### 필수 소프트웨어

- **Python**: 3.9 이상
- **Git**: 버전 관리
- **Docker**: 컨테이너 환경 (선택사항)
- **IDE**: VS Code, PyCharm 등

### 로컬 개발 환경 구축

```bash
# 프로젝트 클론
git clone <repository-url>
cd lora_gateway_logger

# 가상 환경 생성
python -m venv venv

# 가상 환경 활성화
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 개발용 추가 패키지 설치
pip install pytest pytest-cov black flake8 mypy
```

### 환경 변수 설정

개발용 `.env` 파일 생성:

```bash
# .env.development
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_USERNAME=
MQTT_PASSWORD=
ENABLE_SQLITE=true
DATABASE_PATH=./dev_lora_gateway.db
LOG_LEVEL=DEBUG
LOG_FILE=./logs/dev_lora_gateway.log
STATS_INTERVAL=60
```

## 코딩 표준

### Python 코딩 스타일

프로젝트는 PEP 8을 기반으로 하며, 다음 도구들을 사용합니다:

- **Black**: 코드 포매팅
- **Flake8**: 린팅
- **MyPy**: 타입 체킹

### 코드 포매팅

```bash
# Black으로 코드 포매팅
black .

# Flake8로 린팅
flake8 .

# MyPy로 타입 체킹
mypy .
```

### 네이밍 컨벤션

- **클래스**: PascalCase (`LoRaGatewayLogger`)
- **함수/변수**: snake_case (`parse_message`)
- **상수**: UPPER_SNAKE_CASE (`MQTT_TIMEOUT`)
- **모듈**: lowercase (`database.py`)

### 문서화

```python
def process_uplink_message(self, payload: dict) -> bool:
    """
    업링크 메시지를 처리합니다.
    
    Args:
        payload: MQTT에서 수신한 페이로드 딕셔너리
        
    Returns:
        bool: 처리 성공 여부
        
    Raises:
        ValueError: 페이로드 형식이 잘못된 경우
        DatabaseError: 데이터베이스 저장 실패시
    """
    pass
```

## 테스트 가이드

### 테스트 실행

```bash
# 모든 테스트 실행
pytest

# 커버리지 포함
pytest --cov=. --cov-report=html

# 특정 테스트 파일만 실행
pytest test_sqlite.py

# 특정 테스트 함수만 실행
pytest test_sqlite.py::test_insert_uplink_message
```

### 테스트 작성 가이드

1. **단위 테스트**: 각 함수/메서드의 단일 기능 테스트
2. **통합 테스트**: 여러 모듈 간의 상호작용 테스트
3. **E2E 테스트**: 전체 워크플로우 테스트

### 테스트 예시

```python
import pytest
from unittest.mock import Mock, patch
from core.message_parser import LoRaMessageParser

class TestLoRaMessageParser:
    def setup_method(self):
        self.parser = LoRaMessageParser()
    
    def test_parse_topic_valid(self):
        """유효한 토픽 파싱 테스트"""
        topic = "application/1/device/test-device/event/up"
        result = self.parser.parse_topic(topic)
        
        assert result is not None
        app_id, dev_id, event_type = result
        assert app_id == "1"
        assert dev_id == "test-device"
        assert event_type == "up"
    
    def test_parse_topic_invalid(self):
        """잘못된 토픽 파싱 테스트"""
        topic = "invalid/topic"
        result = self.parser.parse_topic(topic)
        
        assert result is None
    
    @patch('core.message_parser.logging')
    def test_parse_payload_json_error(self, mock_logging):
        """JSON 파싱 오류 테스트"""
        invalid_json = b'{"invalid": json}'
        result = self.parser.parse_payload(invalid_json)
        
        assert result is None
        mock_logging.getLogger().error.assert_called()
```

## 브랜치 전략

### Git Flow 브랜치 모델

- **main**: 프로덕션 릴리스 브랜치
- **develop**: 개발 통합 브랜치
- **feature/**: 새로운 기능 개발 브랜치
- **bugfix/**: 버그 수정 브랜치
- **hotfix/**: 긴급 수정 브랜치

### 브랜치 네이밍

```bash
feature/mqtt-reconnection-logic
bugfix/database-connection-timeout
hotfix/critical-memory-leak
```

### 커밋 메시지 컨벤션

```bash
# 타입: 간단한 설명 (50자 이하)
# 
# 상세 설명 (72자로 줄바꿈)
# 
# 이슈 번호 (선택사항)

feat: MQTT 재연결 로직 추가

네트워크 장애시 자동으로 MQTT 브로커에 재연결하는 
기능을 추가했습니다. 지수 백오프 알고리즘을 사용하여
연결 시도 간격을 조절합니다.

Closes #123
```

#### 커밋 타입

- `feat`: 새로운 기능
- `fix`: 버그 수정
- `docs`: 문서 변경
- `style`: 코드 스타일 변경 (기능 변경 없음)
- `refactor`: 리팩토링
- `test`: 테스트 추가/수정
- `chore`: 빌드/설정 변경

## 디버깅 가이드

### 로그 설정

개발 중에는 DEBUG 레벨 로깅을 사용하세요:

```python
import logging

# 개발용 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### MQTT 디버깅

```bash
# MQTT 메시지 모니터링
mosquitto_sub -h localhost -p 1883 -t "application/+/device/+/event/+" -v

# 테스트 메시지 발송
python mock_mqtt_publisher.py
```

### 데이터베이스 디버깅

```bash
# SQLite 데이터베이스 직접 접근
sqlite3 lora_gateway.db

# 테이블 구조 확인
.schema uplink_messages

# 최근 데이터 확인
SELECT * FROM uplink_messages ORDER BY timestamp DESC LIMIT 10;
```

## 성능 최적화

### 프로파일링

```python
import cProfile
import pstats

# 프로파일링 실행
pr = cProfile.Profile()
pr.enable()

# 측정할 코드
your_function()

pr.disable()

# 결과 분석
stats = pstats.Stats(pr)
stats.sort_stats('cumulative')
stats.print_stats(10)
```

### 메모리 사용량 모니터링

```python
import tracemalloc
import psutil
import os

# 메모리 추적 시작
tracemalloc.start()

# 현재 메모리 사용량
process = psutil.Process(os.getpid())
memory_info = process.memory_info()
print(f"RSS: {memory_info.rss / 1024 / 1024:.2f} MB")

# 메모리 사용량 스냅샷
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

for stat in top_stats[:10]:
    print(stat)
```

## 릴리스 가이드

### 버전 관리

프로젝트는 [Semantic Versioning](https://semver.org/)을 따릅니다:

- **MAJOR**: 호환되지 않는 API 변경
- **MINOR**: 하위 호환 기능 추가
- **PATCH**: 하위 호환 버그 수정

### 릴리스 체크리스트

1. **코드 품질 확인**
   - [ ] 모든 테스트 통과
   - [ ] 코드 커버리지 80% 이상
   - [ ] 린팅 오류 없음
   - [ ] 타입 체킹 통과

2. **문서 업데이트**
   - [ ] CHANGELOG.md 업데이트
   - [ ] API 문서 업데이트
   - [ ] README.md 업데이트

3. **보안 검토**
   - [ ] 의존성 취약점 검사
   - [ ] 코드 정적 분석
   - [ ] 시크릿 누출 검사

4. **성능 검증**
   - [ ] 메모리 누수 테스트
   - [ ] 부하 테스트
   - [ ] 성능 회귀 테스트

### 자동화된 품질 검사

```bash
#!/bin/bash
# quality_check.sh

echo "코드 포매팅 검사..."
black --check .

echo "린팅 검사..."
flake8 .

echo "타입 체킹..."
mypy .

echo "테스트 실행..."
pytest --cov=. --cov-report=term-missing

echo "보안 검사..."
bandit -r .

echo "의존성 취약점 검사..."
safety check
```

## 트러블슈팅

### 일반적인 개발 문제

1. **Import 오류**
   ```bash
   # PYTHONPATH 설정
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

2. **테스트 데이터베이스 초기화**
   ```bash
   # 테스트 DB 삭제 후 재생성
   rm test_lora_gateway.db
   python -c "from database import LoRaDatabase; LoRaDatabase('test_lora_gateway.db')"
   ```

3. **MQTT 연결 문제**
   ```bash
   # 로컬 MQTT 브로커 실행
   docker run -it -p 1883:1883 eclipse-mosquitto:2.0
   ```

## IDE 설정

### VS Code 설정

`.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "python.testing.pytestArgs": [
        "."
    ]
}
```

### PyCharm 설정

1. **인터프리터 설정**: Settings → Project → Python Interpreter → 가상 환경 선택
2. **코드 스타일**: Settings → Editor → Code Style → Python → Black 설정
3. **테스트 설정**: Settings → Tools → Python Integrated Tools → pytest 선택

## 기여 가이드

### Pull Request 절차

1. **이슈 생성**: 기능/버그에 대한 이슈 먼저 생성
2. **브랜치 생성**: 이슈 기반 브랜치 생성
3. **개발**: 코딩 표준 준수하여 개발
4. **테스트**: 충분한 테스트 작성 및 실행
5. **PR 생성**: 상세한 설명과 함께 PR 생성
6. **리뷰**: 코드 리뷰 수행
7. **머지**: 리뷰 완료 후 머지

### 코드 리뷰 가이드

**리뷰어 체크리스트:**
- [ ] 코드가 요구사항을 만족하는가?
- [ ] 테스트가 충분한가?
- [ ] 성능상 문제는 없는가?
- [ ] 보안 취약점은 없는가?
- [ ] 문서화가 적절한가?

## 도구 및 유틸리티

### 개발 도구 스크립트

```bash
#!/bin/bash
# dev_tools.sh

case "$1" in
    "format")
        black .
        ;;
    "lint")
        flake8 .
        ;;
    "type-check")
        mypy .
        ;;
    "test")
        pytest --cov=. --cov-report=html
        ;;
    "test-watch")
        pytest-watch
        ;;
    "clean")
        find . -type d -name __pycache__ -delete
        find . -name "*.pyc" -delete
        ;;
    *)
        echo "Usage: $0 {format|lint|type-check|test|test-watch|clean}"
        ;;
esac
```

### 유용한 별칭

```bash
# ~/.bashrc 또는 ~/.zshrc
alias lora-format="black ."
alias lora-lint="flake8 ."
alias lora-test="pytest --cov=. --cov-report=term-missing"
alias lora-run="python main.py"
```