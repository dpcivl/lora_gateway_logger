"""
SQLite 데이터베이스 관리 모듈
LoRa 업링크 메시지를 SQLite DB에 저장하고 조회하는 기능 제공
"""
import sqlite3
import logging
from datetime import datetime
from typing import Optional, List
from dataclasses import asdict
from models import UplinkMessage, JoinEvent


class LoRaDatabase:
    def __init__(self, db_path: str = "lora_gateway.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()
        
    def close(self):
        """데이터베이스 연결 정리 (테스트용)"""
        # SQLite는 connection pooling을 하지 않으므로 특별한 정리 불필요
        pass
    
    def _init_database(self):
        """데이터베이스 초기화 및 테이블 생성"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS uplink_messages (
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
                    )
                """)
                
                # 인덱스 생성
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_device_timestamp 
                    ON uplink_messages(device_id, timestamp)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_application_timestamp 
                    ON uplink_messages(application_id, timestamp)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp 
                    ON uplink_messages(timestamp)
                """)
                
                # JOIN 이벤트 테이블 생성
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS join_events (
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
                    )
                """)
                
                # JOIN 이벤트 인덱스 생성
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_join_device_timestamp 
                    ON join_events(device_id, timestamp)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_join_timestamp 
                    ON join_events(timestamp)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_join_dev_eui 
                    ON join_events(dev_eui)
                """)
                
                conn.commit()
                self.logger.info("SQLite 데이터베이스 초기화 완료 (업링크 + JOIN 테이블)")
                
        except Exception as e:
            self.logger.error(f"데이터베이스 초기화 오류: {e}")
            raise
    
    def insert_uplink_message(self, message: UplinkMessage) -> Optional[int]:
        """업링크 메시지를 데이터베이스에 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # dataclass를 dict로 변환 (id, created_at 제외)
                data = asdict(message)
                data.pop('id', None)
                data.pop('created_at', None)
                
                # timestamp를 문자열로 변환
                if isinstance(data['timestamp'], datetime):
                    data['timestamp'] = data['timestamp'].isoformat()
                
                columns = list(data.keys())
                placeholders = ['?' for _ in columns]
                values = list(data.values())
                
                query = f"""
                    INSERT INTO uplink_messages ({', '.join(columns)})
                    VALUES ({', '.join(placeholders)})
                """
                
                cursor = conn.execute(query, values)
                conn.commit()
                
                row_id = cursor.lastrowid
                self.logger.debug(f"업링크 메시지 저장 완료 - ID: {row_id}")
                return row_id
                
        except Exception as e:
            self.logger.error(f"업링크 메시지 저장 오류: {e}")
            return None
    
    def insert_join_event(self, event: JoinEvent) -> Optional[int]:
        """JOIN 이벤트를 데이터베이스에 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # dataclass를 dict로 변환 (id, created_at 제외)
                data = asdict(event)
                data.pop('id', None)
                data.pop('created_at', None)
                
                # timestamp를 문자열로 변환
                if isinstance(data['timestamp'], datetime):
                    data['timestamp'] = data['timestamp'].isoformat()
                
                columns = list(data.keys())
                placeholders = ['?' for _ in columns]
                values = list(data.values())
                
                query = f"""
                    INSERT INTO join_events ({', '.join(columns)})
                    VALUES ({', '.join(placeholders)})
                """
                
                cursor = conn.execute(query, values)
                conn.commit()
                
                row_id = cursor.lastrowid
                self.logger.debug(f"JOIN 이벤트 저장 완료 - ID: {row_id}")
                return row_id
                
        except Exception as e:
            self.logger.error(f"JOIN 이벤트 저장 오류: {e}")
            return None
    
    def get_recent_messages(self, limit: int = 100) -> List[UplinkMessage]:
        """최근 메시지 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM uplink_messages 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (limit,))
                
                rows = cursor.fetchall()
                return [self._row_to_message(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"메시지 조회 오류: {e}")
            return []
    
    def get_device_messages(self, device_id: str, limit: int = 100) -> List[UplinkMessage]:
        """특정 디바이스의 메시지 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM uplink_messages 
                    WHERE device_id = ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (device_id, limit))
                
                rows = cursor.fetchall()
                return [self._row_to_message(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"디바이스 메시지 조회 오류: {e}")
            return []
    
    def get_recent_join_events(self, limit: int = 100) -> List[JoinEvent]:
        """최근 JOIN 이벤트 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM join_events 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (limit,))
                
                rows = cursor.fetchall()
                return [self._row_to_join_event(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"JOIN 이벤트 조회 오류: {e}")
            return []
    
    def get_device_join_events(self, device_id: str, limit: int = 100) -> List[JoinEvent]:
        """특정 디바이스의 JOIN 이벤트 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM join_events 
                    WHERE device_id = ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (device_id, limit))
                
                rows = cursor.fetchall()
                return [self._row_to_join_event(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"디바이스 JOIN 이벤트 조회 오류: {e}")
            return []
    
    def get_statistics(self) -> dict:
        """기본 통계 정보 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 업링크 메시지 통계
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_messages,
                        COUNT(DISTINCT device_id) as unique_devices,
                        COUNT(DISTINCT application_id) as unique_applications,
                        MIN(timestamp) as first_message,
                        MAX(timestamp) as last_message
                    FROM uplink_messages
                """)
                uplink_stats = cursor.fetchone()
                
                # JOIN 이벤트 통계
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_joins,
                        COUNT(DISTINCT device_id) as unique_join_devices,
                        MIN(timestamp) as first_join,
                        MAX(timestamp) as last_join
                    FROM join_events
                """)
                join_stats = cursor.fetchone()
                
                return {
                    'total_messages': uplink_stats[0],
                    'unique_devices': uplink_stats[1],
                    'unique_applications': uplink_stats[2],
                    'first_message': uplink_stats[3],
                    'last_message': uplink_stats[4],
                    'total_joins': join_stats[0],
                    'unique_join_devices': join_stats[1],
                    'first_join': join_stats[2],
                    'last_join': join_stats[3]
                }
                
        except Exception as e:
            self.logger.error(f"통계 조회 오류: {e}")
            return {}
    
    def _row_to_message(self, row: sqlite3.Row) -> UplinkMessage:
        """SQLite Row를 UplinkMessage 객체로 변환"""
        return UplinkMessage(
            id=row['id'],
            timestamp=datetime.fromisoformat(row['timestamp']) if row['timestamp'] else None,
            application_id=row['application_id'],
            device_id=row['device_id'],
            dev_eui=row['dev_eui'],
            payload_base64=row['payload_base64'],
            payload_hex=row['payload_hex'],
            payload_text=row['payload_text'],
            payload_size=row['payload_size'],
            frame_count=row['frame_count'],
            f_port=row['f_port'],
            frequency=row['frequency'],
            data_rate=row['data_rate'],
            rssi=row['rssi'],
            snr=row['snr'],
            latitude=row['latitude'],
            longitude=row['longitude'],
            hostname=row['hostname'],
            raw_topic=row['raw_topic'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        )
    
    def _row_to_join_event(self, row: sqlite3.Row) -> JoinEvent:
        """SQLite Row를 JoinEvent 객체로 변환"""
        return JoinEvent(
            id=row['id'],
            timestamp=datetime.fromisoformat(row['timestamp']) if row['timestamp'] else None,
            application_id=row['application_id'],
            device_id=row['device_id'],
            dev_eui=row['dev_eui'],
            join_eui=row['join_eui'],
            dev_addr=row['dev_addr'],
            frequency=row['frequency'],
            data_rate=row['data_rate'],
            rssi=row['rssi'],
            snr=row['snr'],
            latitude=row['latitude'],
            longitude=row['longitude'],
            hostname=row['hostname'],
            raw_topic=row['raw_topic'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        )