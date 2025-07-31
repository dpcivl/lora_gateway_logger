# 데이터베이스 연결 정보

## 개요

LoRa Gateway Logger는 SQLite를 사용하여 데이터를 저장합니다. 데이터베이스 연결 설정은 환경 변수를 통해 관리됩니다.

## 환경 변수 설정

### 데이터베이스 관련 환경 변수

| 환경 변수 | 기본값 | 설명 |
|-----------|--------|------|
| `ENABLE_SQLITE` | `true` | SQLite 데이터베이스 사용 여부 |
| `DATABASE_PATH` | `lora_gateway.db` | SQLite 데이터베이스 파일 경로 |

### 설정 예시

```bash
# SQLite 활성화
export ENABLE_SQLITE=true

# 데이터베이스 파일 경로 설정
export DATABASE_PATH=/path/to/your/lora_gateway.db

# 또는 상대 경로 사용
export DATABASE_PATH=./data/lora_gateway.db
```

## 데이터베이스 파일 관리

### 기본 설정
- 데이터베이스 파일: `lora_gateway.db`
- 위치: 프로젝트 루트 디렉터리
- 형식: SQLite3

### 권한 설정
SQLite 파일에 대한 읽기/쓰기 권한이 필요합니다:

```bash
# 파일 권한 확인
ls -la lora_gateway.db

# 권한 설정 (필요시)
chmod 664 lora_gateway.db
```

### 백업 및 복원

#### 백업
```bash
# SQLite 데이터베이스 백업
cp lora_gateway.db lora_gateway_backup_$(date +%Y%m%d_%H%M%S).db

# 또는 SQL 덤프 생성
sqlite3 lora_gateway.db .dump > lora_gateway_backup.sql
```

#### 복원
```bash
# 백업 파일에서 복원
cp lora_gateway_backup_20240131_143000.db lora_gateway.db

# SQL 덤프에서 복원
sqlite3 new_lora_gateway.db < lora_gateway_backup.sql
```

## 연결 코드 예시

### Python에서 연결

```python
from database import LoRaDatabase

# 기본 설정으로 연결
db = LoRaDatabase()

# 사용자 정의 경로로 연결
db = LoRaDatabase(db_path="/custom/path/lora_gateway.db")

# 통계 정보 조회
stats = db.get_statistics()
print(f"총 메시지 수: {stats['total_messages']}")

# 최근 메시지 조회
recent_messages = db.get_recent_messages(limit=10)
```

### 직접 SQLite 연결

```python
import sqlite3
from datetime import datetime

# 데이터베이스 연결
conn = sqlite3.connect('lora_gateway.db')
conn.row_factory = sqlite3.Row

# 쿼리 실행
cursor = conn.execute("""
    SELECT device_id, COUNT(*) as message_count 
    FROM uplink_messages 
    GROUP BY device_id 
    ORDER BY message_count DESC
""")

results = cursor.fetchall()
for row in results:
    print(f"Device: {row['device_id']}, Messages: {row['message_count']}")

conn.close()
```

## 웹 애플리케이션에서 사용

Java + JavaScript 웹 애플리케이션에서 SQLite 데이터베이스를 사용하는 방법:

### Java (Spring Boot) 설정

```yaml
# application.yml
spring:
  datasource:
    url: jdbc:sqlite:lora_gateway.db
    driver-class-name: org.sqlite.JDBC
  jpa:
    database-platform: org.hibernate.dialect.SQLiteDialect
    hibernate:
      ddl-auto: validate
```

```xml
<!-- pom.xml dependencies -->
<dependency>
    <groupId>org.xerial</groupId>
    <artifactId>sqlite-jdbc</artifactId>
    <version>3.41.2.2</version>
</dependency>
```

### Java Entity 예시

```java
@Entity
@Table(name = "uplink_messages")
public class UplinkMessage {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(name = "timestamp")
    private LocalDateTime timestamp;
    
    @Column(name = "application_id")
    private String applicationId;
    
    @Column(name = "device_id")
    private String deviceId;
    
    // getter, setter, constructors...
}
```

## 성능 최적화

### 인덱스 활용
성능 향상을 위해 미리 생성된 인덱스를 활용하세요:
- 디바이스별 조회: `device_id` + `timestamp`
- 애플리케이션별 조회: `application_id` + `timestamp`
- 시간 범위 조회: `timestamp`

### 연결 풀링
Java 애플리케이션에서는 HikariCP를 사용한 연결 풀링을 권장합니다:

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 10
      minimum-idle: 5
      connection-timeout: 30000
```

## 보안 고려사항

### 파일 권한
```bash
# 데이터베이스 파일 보안 설정
chmod 640 lora_gateway.db
chown app_user:app_group lora_gateway.db
```

### 백업 보안
- 백업 파일 암호화
- 안전한 저장소에 백업
- 정기적인 백업 파일 정리

## 모니터링

### 데이터베이스 크기 확인
```bash
# 파일 크기 확인
ls -lh lora_gateway.db

# SQLite 내부 정보 확인
sqlite3 lora_gateway.db "PRAGMA database_list;"
sqlite3 lora_gateway.db "PRAGMA table_info(uplink_messages);"
```

### 성능 모니터링
```sql
-- 테이블별 레코드 수
SELECT 'uplink_messages' as table_name, COUNT(*) as count FROM uplink_messages
UNION ALL
SELECT 'join_events' as table_name, COUNT(*) as count FROM join_events;

-- 인덱스 사용 확인
EXPLAIN QUERY PLAN SELECT * FROM uplink_messages WHERE device_id = 'test' ORDER BY timestamp DESC;
```