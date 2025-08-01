# 웹 통합 가이드

## 개요

이 문서는 LoRa Gateway Logger와 Java + JavaScript 웹 애플리케이션을 통합하는 방법을 설명합니다.

## 아키텍처 개요

```
LoRa Device → LoRaWAN Gateway → MQTT Broker → LoRa Gateway Logger → SQLite Database
                                                                          ↓
                                                              Java Spring Boot API
                                                                          ↓
                                                              JavaScript Frontend
```

## Java 백엔드 통합

### Spring Boot 프로젝트 설정

#### 의존성 (pom.xml)

```xml
<dependencies>
    <!-- Spring Boot Starters -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-jpa</artifactId>
    </dependency>
    
    <!-- SQLite -->
    <dependency>
        <groupId>org.xerial</groupId>
        <artifactId>sqlite-jdbc</artifactId>
        <version>3.41.2.2</version>
    </dependency>
    
    <!-- SQLite Dialect -->
    <dependency>
        <groupId>org.hibernate.orm</groupId>
        <artifactId>hibernate-community-dialects</artifactId>
    </dependency>
    
    <!-- WebSocket (실시간 데이터용) -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-websocket</artifactId>
    </dependency>
    
    <!-- JSON Processing -->
    <dependency>
        <groupId>com.fasterxml.jackson.core</groupId>
        <artifactId>jackson-databind</artifactId>
    </dependency>
</dependencies>
```

#### 애플리케이션 설정 (application.yml)

```yaml
spring:
  datasource:
    url: jdbc:sqlite:lora_gateway.db
    driver-class-name: org.sqlite.JDBC
  jpa:
    database-platform: org.hibernate.community.dialect.SQLiteDialect
    hibernate:
      ddl-auto: validate
    show-sql: false
  jackson:
    date-format: yyyy-MM-dd'T'HH:mm:ss.SSS'Z'
    time-zone: UTC

server:
  port: 8081  # Chirpstack이 8080을 사용하므로 8081 사용
  servlet:
    context-path: /api

logging:
  level:
    com.yourcompany.lora: DEBUG
    org.springframework.web: INFO
```

### JPA Entity 정의

#### UplinkMessage Entity

```java
package com.yourcompany.lora.entity;

import javax.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "uplink_messages")
public class UplinkMessage {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(name = "timestamp", nullable = false)
    private LocalDateTime timestamp;
    
    @Column(name = "application_id", nullable = false)
    private String applicationId;
    
    @Column(name = "device_id", nullable = false)
    private String deviceId;
    
    @Column(name = "dev_eui")
    private String devEui;
    
    @Column(name = "payload_base64")
    private String payloadBase64;
    
    @Column(name = "payload_hex")
    private String payloadHex;
    
    @Column(name = "payload_text")
    private String payloadText;
    
    @Column(name = "payload_size")
    private Integer payloadSize;
    
    @Column(name = "frame_count")
    private Integer frameCount;
    
    @Column(name = "f_port")
    private Integer fPort;
    
    @Column(name = "frequency")
    private Integer frequency;
    
    @Column(name = "data_rate")
    private Integer dataRate;
    
    @Column(name = "rssi")
    private Float rssi;
    
    @Column(name = "snr")
    private Float snr;
    
    @Column(name = "latitude")
    private Float latitude;
    
    @Column(name = "longitude")
    private Float longitude;
    
    @Column(name = "hostname")
    private String hostname;
    
    @Column(name = "raw_topic")
    private String rawTopic;
    
    @Column(name = "created_at")
    private LocalDateTime createdAt;
    
    // Constructors, getters, setters
    
    public SignalQuality getSignalQuality() {
        if (rssi != null && snr != null) {
            if (rssi > -70 && snr > 10) return SignalQuality.EXCELLENT;
            if (rssi > -85 && snr > 5) return SignalQuality.GOOD;
            if (rssi > -100 && snr > 0) return SignalQuality.FAIR;
        }
        return SignalQuality.POOR;
    }
}

enum SignalQuality {
    EXCELLENT, GOOD, FAIR, POOR
}
```

#### JoinEvent Entity

```java
@Entity
@Table(name = "join_events")
public class JoinEvent {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(name = "timestamp", nullable = false)
    private LocalDateTime timestamp;
    
    @Column(name = "application_id", nullable = false)
    private String applicationId;
    
    @Column(name = "device_id", nullable = false)
    private String deviceId;
    
    @Column(name = "dev_eui", nullable = false)
    private String devEui;
    
    @Column(name = "join_eui")
    private String joinEui;
    
    @Column(name = "dev_addr")
    private String devAddr;
    
    // ... 기타 필드들 (UplinkMessage와 유사)
    
    // Constructors, getters, setters
}
```

### Repository 인터페이스

```java
package com.yourcompany.lora.repository;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import java.time.LocalDateTime;
import java.util.List;

public interface UplinkMessageRepository extends JpaRepository<UplinkMessage, Long> {
    
    // 디바이스별 최근 메시지 조회
    Page<UplinkMessage> findByDeviceIdOrderByTimestampDesc(
        String deviceId, Pageable pageable);
    
    // 애플리케이션별 메시지 조회
    Page<UplinkMessage> findByApplicationIdOrderByTimestampDesc(
        String applicationId, Pageable pageable);
    
    // 시간 범위별 조회
    List<UplinkMessage> findByTimestampBetweenOrderByTimestampDesc(
        LocalDateTime startTime, LocalDateTime endTime);
    
    // 디바이스 통계
    @Query("SELECT m.deviceId, COUNT(m) as count FROM UplinkMessage m " +
           "WHERE m.timestamp >= :since GROUP BY m.deviceId")
    List<Object[]> getDeviceMessageCounts(@Param("since") LocalDateTime since);
    
    // 신호 품질별 통계
    @Query("SELECT " +
           "COUNT(CASE WHEN m.rssi > -70 AND m.snr > 10 THEN 1 END) as excellent, " +
           "COUNT(CASE WHEN m.rssi > -85 AND m.snr > 5 THEN 1 END) as good, " +
           "COUNT(CASE WHEN m.rssi > -100 AND m.snr > 0 THEN 1 END) as fair, " +
           "COUNT(CASE WHEN m.rssi <= -100 OR m.snr <= 0 THEN 1 END) as poor " +
           "FROM UplinkMessage m WHERE m.timestamp >= :since")
    Object[] getSignalQualityStats(@Param("since") LocalDateTime since);
}
```

### REST API Controller

```java
package com.yourcompany.lora.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/messages")
@CrossOrigin(origins = "*")
public class MessageController {
    
    @Autowired
    private UplinkMessageRepository messageRepository;
    
    @Autowired
    private JoinEventRepository joinEventRepository;
    
    // 최근 메시지 조회
    @GetMapping("/recent")
    public ResponseEntity<Page<UplinkMessage>> getRecentMessages(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        
        Pageable pageable = PageRequest.of(page, size);
        Page<UplinkMessage> messages = messageRepository.findAll(pageable);
        return ResponseEntity.ok(messages);
    }
    
    // 디바이스별 메시지 조회
    @GetMapping("/device/{deviceId}")
    public ResponseEntity<Page<UplinkMessage>> getDeviceMessages(
            @PathVariable String deviceId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        
        Pageable pageable = PageRequest.of(page, size);
        Page<UplinkMessage> messages = messageRepository
            .findByDeviceIdOrderByTimestampDesc(deviceId, pageable);
        return ResponseEntity.ok(messages);
    }
    
    // 통계 정보 조회
    @GetMapping("/statistics")
    public ResponseEntity<Map<String, Object>> getStatistics() {
        LocalDateTime last24Hours = LocalDateTime.now().minusHours(24);
        
        long totalMessages = messageRepository.count();
        long last24HourMessages = messageRepository
            .findByTimestampBetweenOrderByTimestampDesc(last24Hours, LocalDateTime.now())
            .size();
        
        List<Object[]> deviceCounts = messageRepository.getDeviceMessageCounts(last24Hours);
        Object[] signalStats = messageRepository.getSignalQualityStats(last24Hours);
        
        Map<String, Object> stats = Map.of(
            "totalMessages", totalMessages,
            "last24HourMessages", last24HourMessages,
            "deviceCounts", deviceCounts,
            "signalQuality", Map.of(
                "excellent", signalStats[0],
                "good", signalStats[1],
                "fair", signalStats[2],
                "poor", signalStats[3]
            )
        );
        
        return ResponseEntity.ok(stats);
    }
    
    // 실시간 데이터 스트림 (Server-Sent Events)
    @GetMapping(value = "/stream", produces = "text/event-stream")
    public SseEmitter streamMessages() {
        SseEmitter emitter = new SseEmitter(Long.MAX_VALUE);
        
        // 실시간 데이터 스트리밍 로직
        // (별도 서비스에서 구현)
        
        return emitter;
    }
}
```

### WebSocket 설정 (실시간 업데이트)

```java
package com.yourcompany.lora.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {
    
    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(new MessageWebSocketHandler(), "/ws/messages")
                .setAllowedOrigins("*");  // Chirpstack과 구분되는 WebSocket 엔드포인트
    }
}

@Component
public class MessageWebSocketHandler extends TextWebSocketHandler {
    
    private final Set<WebSocketSession> sessions = new HashSet<>();
    
    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        sessions.add(session);
    }
    
    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        sessions.remove(session);
    }
    
    public void broadcastMessage(UplinkMessage message) {
        String jsonMessage = convertToJson(message);
        sessions.forEach(session -> {
            try {
                session.sendMessage(new TextMessage(jsonMessage));
            } catch (IOException e) {
                // Handle error
            }
        });
    }
}
```

## JavaScript 프론트엔드 통합

### React 컴포넌트 예시

#### 메시지 목록 컴포넌트

```jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const MessageList = () => {
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(0);
    const [totalPages, setTotalPages] = useState(0);

    useEffect(() => {
        fetchMessages();
    }, [page]);

    const fetchMessages = async () => {
        try {
            setLoading(true);
            const response = await axios.get(`/api/messages/recent?page=${page}&size=20`);
            setMessages(response.data.content);
            setTotalPages(response.data.totalPages);
        } catch (error) {
            console.error('메시지 조회 실패:', error);
        } finally {
            setLoading(false);
        }
    };

    const formatSignalQuality = (rssi, snr) => {
        if (rssi > -70 && snr > 10) return { text: '매우 좋음', color: 'green' };
        if (rssi > -85 && snr > 5) return { text: '좋음', color: 'blue' };
        if (rssi > -100 && snr > 0) return { text: '보통', color: 'orange' };
        return { text: '나쁨', color: 'red' };
    };

    if (loading) return <div>로딩 중...</div>;

    return (
        <div className="message-list">
            <h2>최근 LoRa 메시지</h2>
            
            <table className="table">
                <thead>
                    <tr>
                        <th>시간</th>
                        <th>디바이스 ID</th>
                        <th>메시지</th>
                        <th>RSSI</th>
                        <th>SNR</th>
                        <th>신호 품질</th>
                    </tr>
                </thead>
                <tbody>
                    {messages.map(message => {
                        const quality = formatSignalQuality(message.rssi, message.snr);
                        return (
                            <tr key={message.id}>
                                <td>{new Date(message.timestamp).toLocaleString()}</td>
                                <td>{message.deviceId}</td>
                                <td>{message.payloadText || '[바이너리 데이터]'}</td>
                                <td>{message.rssi} dBm</td>
                                <td>{message.snr} dB</td>
                                <td style={{ color: quality.color }}>{quality.text}</td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
            
            {/* 페이지네이션 */}
            <div className="pagination">
                <button 
                    disabled={page === 0} 
                    onClick={() => setPage(page - 1)}>
                    이전
                </button>
                <span>{page + 1} / {totalPages}</span>
                <button 
                    disabled={page >= totalPages - 1} 
                    onClick={() => setPage(page + 1)}>
                    다음
                </button>
            </div>
        </div>
    );
};

export default MessageList;
```

#### 실시간 대시보드 컴포넌트

```jsx
import React, { useState, useEffect } from 'react';
import { Line } from 'react-chartjs-2';

const RealtimeDashboard = () => {
    const [ws, setWs] = useState(null);
    const [realtimeData, setRealtimeData] = useState([]);
    const [statistics, setStatistics] = useState({});

    useEffect(() => {
        // WebSocket 연결 (Chirpstack 충돌 방지로 8081 사용)
        const websocket = new WebSocket('ws://localhost:8081/ws/messages');
        
        websocket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            setRealtimeData(prev => [...prev.slice(-49), message]); // 최근 50개 유지
        };
        
        websocket.onerror = (error) => {
            console.error('WebSocket 오류:', error);
        };
        
        setWs(websocket);
        
        // 통계 데이터 주기적 조회
        const statsInterval = setInterval(fetchStatistics, 30000); // 30초마다
        fetchStatistics(); // 초기 로드
        
        return () => {
            websocket.close();
            clearInterval(statsInterval);
        };
    }, []);

    const fetchStatistics = async () => {
        try {
            const response = await axios.get('/api/messages/statistics');
            setStatistics(response.data);
        } catch (error) {
            console.error('통계 조회 실패:', error);
        }
    };

    const chartData = {
        labels: realtimeData.map((_, index) => index),
        datasets: [
            {
                label: 'RSSI (dBm)',
                data: realtimeData.map(msg => msg.rssi),
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1
            },
            {
                label: 'SNR (dB)',
                data: realtimeData.map(msg => msg.snr),
                borderColor: 'rgb(255, 99, 132)',
                tension: 0.1
            }
        ]
    };

    return (
        <div className="dashboard">
            <h2>실시간 LoRa 대시보드</h2>
            
            {/* 통계 카드 */}
            <div className="stats-cards">
                <div className="card">
                    <h3>총 메시지</h3>
                    <p>{statistics.totalMessages?.toLocaleString()}</p>
                </div>
                <div className="card">
                    <h3>24시간 메시지</h3>
                    <p>{statistics.last24HourMessages?.toLocaleString()}</p>
                </div>
                <div className="card">
                    <h3>활성 디바이스</h3>
                    <p>{statistics.deviceCounts?.length}</p>
                </div>
            </div>
            
            {/* 실시간 차트 */}
            <div className="chart-container">
                <h3>실시간 신호 품질</h3>
                <Line data={chartData} options={{
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }} />
            </div>
            
            {/* 신호 품질 분포 */}
            <div className="signal-quality">
                <h3>신호 품질 분포</h3>
                <div className="quality-bars">
                    <div className="quality-bar excellent">
                        <span>매우 좋음: {statistics.signalQuality?.excellent}</span>
                    </div>
                    <div className="quality-bar good">
                        <span>좋음: {statistics.signalQuality?.good}</span>
                    </div>
                    <div className="quality-bar fair">
                        <span>보통: {statistics.signalQuality?.fair}</span>
                    </div>
                    <div className="quality-bar poor">
                        <span>나쁨: {statistics.signalQuality?.poor}</span>
                    </div>
                </div>
            </div>
            
            {/* 최근 메시지 목록 */}
            <div className="recent-messages">
                <h3>실시간 메시지</h3>
                <div className="message-stream">
                    {realtimeData.slice(-10).reverse().map(msg => (
                        <div key={msg.id} className="message-item">
                            <span className="timestamp">
                                {new Date(msg.timestamp).toLocaleTimeString()}
                            </span>
                            <span className="device">{msg.deviceId}</span>
                            <span className="payload">{msg.payloadText}</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default RealtimeDashboard;
```

### API 클라이언트 설정

```javascript
// api/client.js
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8081/api';  // Chirpstack 충돌 방지

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
    }
});

// 요청 인터셉터
apiClient.interceptors.request.use(
    config => {
        console.log(`API 요청: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
    },
    error => {
        return Promise.reject(error);
    }
);

// 응답 인터셉터
apiClient.interceptors.response.use(
    response => {
        return response;
    },
    error => {
        console.error('API 오류:', error.response?.status, error.message);
        return Promise.reject(error);
    }
);

export const messageAPI = {
    getRecentMessages: (page = 0, size = 20) => 
        apiClient.get(`/messages/recent?page=${page}&size=${size}`),
    
    getDeviceMessages: (deviceId, page = 0, size = 20) => 
        apiClient.get(`/messages/device/${deviceId}?page=${page}&size=${size}`),
    
    getStatistics: () => 
        apiClient.get('/messages/statistics'),
    
    getDeviceList: () => 
        apiClient.get('/devices'),
    
    getJoinEvents: (page = 0, size = 20) => 
        apiClient.get(`/join-events/recent?page=${page}&size=${size}`)
};

export default apiClient;
```

## 데이터 동기화 전략

### 실시간 데이터 업데이트

1. **WebSocket 연결**: 실시간 메시지 스트리밍
2. **Server-Sent Events**: 단방향 실시간 업데이트
3. **Polling**: 주기적 API 호출 (fallback)

### 캐싱 전략

```javascript
// 클라이언트 사이드 캐싱
class DataCache {
    constructor() {
        this.cache = new Map();
        this.expiry = new Map();
    }
    
    set(key, data, ttl = 300000) { // 5분 TTL
        this.cache.set(key, data);
        this.expiry.set(key, Date.now() + ttl);
    }
    
    get(key) {
        if (this.expiry.get(key) < Date.now()) {
            this.cache.delete(key);
            this.expiry.delete(key);
            return null;
        }
        return this.cache.get(key);
    }
}

const dataCache = new DataCache();
```

## 보안 고려사항

### CORS 설정

```java
@Configuration
public class WebConfig implements WebMvcConfigurer {
    
    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
                .allowedOrigins(
                    "http://localhost:3000",           // React 개발 서버
                    "http://localhost:8080",           // Chirpstack (필요시)
                    "https://yourdomain.com"
                )
                .allowedMethods("GET", "POST", "PUT", "DELETE")
                .allowedHeaders("*")
                .allowCredentials(true);
    }
}
```

### 인증 및 권한 (선택사항)

```java
// JWT 기반 인증 (필요시)
@RestController
@RequestMapping("/auth")
public class AuthController {
    
    @PostMapping("/login")
    public ResponseEntity<JwtResponse> login(@RequestBody LoginRequest request) {
        // 인증 로직
        // JWT 토큰 생성 및 반환
    }
}
```

## 성능 최적화

### 데이터베이스 쿼리 최적화

```java
// 페이징 처리
@Query("SELECT m FROM UplinkMessage m WHERE m.deviceId = :deviceId " +
       "ORDER BY m.timestamp DESC")
Page<UplinkMessage> findByDeviceIdWithPaging(
    @Param("deviceId") String deviceId, Pageable pageable);

// 인덱스 활용
@Table(name = "uplink_messages", indexes = {
    @Index(name = "idx_device_timestamp", columnList = "device_id, timestamp"),
    @Index(name = "idx_timestamp", columnList = "timestamp")
})
```

### 프론트엔드 최적화

```javascript
// React.memo를 사용한 컴포넌트 최적화
const MessageItem = React.memo(({ message }) => {
    return (
        <div className="message-item">
            <span>{message.deviceId}</span>
            <span>{message.payloadText}</span>
        </div>
    );
});

// 가상화를 통한 대용량 리스트 처리
import { FixedSizeList as List } from 'react-window';

const MessageList = ({ messages }) => (
    <List
        height={600}
        itemCount={messages.length}
        itemSize={50}
        itemData={messages}
    >
        {MessageItem}
    </List>
);
```

## 배포 가이드

### Docker Compose 전체 스택

```yaml
version: '3.8'

services:
  mosquitto:
    image: eclipse-mosquitto:2.0
    ports:
      - "1883:1883"
      - "9001:9001"
    volumes:
      - ./mosquitto.conf:/mosquitto/config/mosquitto.conf
    
  lora-gateway-logger:
    build: ./lora_gateway_logger
    depends_on:
      - mosquitto
    environment:
      - MQTT_BROKER_HOST=mosquitto
      - MQTT_BROKER_PORT=1883
    volumes:
      - ./data:/app/data
    
  backend:
    build: ./backend
    ports:
      - "8081:8080"  # Chirpstack 충돌 방지로 8081 사용
    environment:
      - SPRING_DATASOURCE_URL=jdbc:sqlite:/app/data/lora_gateway.db
    volumes:
      - ./data:/app/data
    depends_on:
      - lora-gateway-logger
    
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    environment:
      - REACT_APP_API_URL=http://localhost:8081/api  # 8081 포트 사용
    depends_on:
      - backend
```

### 프로덕션 배포 고려사항

1. **리버스 프록시**: Nginx 또는 Apache 사용
2. **SSL/TLS**: HTTPS 설정
3. **로드 밸런싱**: 다중 인스턴스 운영
4. **모니터링**: 애플리케이션 및 인프라 모니터링
5. **백업**: 데이터베이스 정기 백업