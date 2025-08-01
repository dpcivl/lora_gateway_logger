"""
데이터 처리 및 저장 모듈
파싱된 LoRa 데이터를 SQLite 및 JSON 파일에 저장
"""
import json
import logging
import socket
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional

# SQLite 연동 모듈 (optional)
try:
    from database import LoRaDatabase
    from models import UplinkMessage, JoinEvent
    SQLITE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"SQLite 모듈을 로드할 수 없습니다: {e}. JSON 로깅만 사용합니다.")
    SQLITE_AVAILABLE = False


class LoRaDataProcessor:
    def __init__(self, enable_sqlite: bool = True, db_path: str = "lora_gateway.db"):
        self.logger = logging.getLogger(__name__)
        
        # SQLite 데이터베이스 초기화
        self.db = None
        if enable_sqlite and SQLITE_AVAILABLE:
            try:
                self.db = LoRaDatabase(db_path)
                self.logger.info("SQLite 데이터베이스 연동 활성화")
            except Exception as e:
                self.logger.error(f"SQLite 데이터베이스 초기화 실패: {e}")
                self.db = None
        
        # 통계 정보
        self.stats = {
            'messages_received': 0,
            'messages_processed': 0,
            'joins_received': 0,
            'joins_processed': 0,
            'sqlite_saves': 0,
            'json_saves': 0,
            'errors': 0,
            'last_message_time': None
        }
    
    def process_uplink_message(self, application_id: str, device_id: str, 
                              topic: str, payload_summary: Dict):
        """업링크 메시지 처리 및 저장"""
        # KST 타임존 설정 (UTC+9)
        kst = timezone(timedelta(hours=9))
        now_kst = datetime.now(kst)
        
        self.stats['messages_received'] += 1
        self.stats['last_message_time'] = now_kst
        
        try:
            # 로그 데이터 구성
            log_data = {
                "timestamp": now_kst.isoformat(),
                "topic": topic,
                "application_id": application_id,
                "device_id": device_id,
                "payload": payload_summary,
                "raw_payload_size": len(str(payload_summary)),
                "hostname": socket.gethostname()
            }
            
            # 주요 정보 로깅
            self._log_uplink_info(application_id, device_id, payload_summary)
            
            # 데이터 저장 (SQLite + JSON 병행)
            self._save_uplink_data(payload_summary, application_id, device_id, topic, log_data)
            self.stats['messages_processed'] += 1
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"업링크 메시지 처리 오류: {e}", exc_info=True)
    
    def process_join_event(self, application_id: str, device_id: str, 
                          topic: str, join_summary: Dict):
        """JOIN 이벤트 처리 및 저장"""
        # KST 타임존 설정 (UTC+9)
        kst = timezone(timedelta(hours=9))
        now_kst = datetime.now(kst)
        
        self.stats['joins_received'] += 1
        self.stats['last_message_time'] = now_kst
        
        try:
            # JOIN 이벤트 정보 로깅
            self._log_join_info(application_id, device_id, join_summary)
            
            # JOIN 이벤트 저장
            self._save_join_event(join_summary, application_id, device_id, topic)
            self.stats['joins_processed'] += 1
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"JOIN 이벤트 처리 오류: {e}", exc_info=True)
    
    def _log_uplink_info(self, application_id: str, device_id: str, payload_summary: Dict):
        """업링크 메시지 정보 로깅"""
        self.logger.info(f"LoRa 업링크 데이터 수신 - App: {application_id}, Device: {device_id}")
        self.logger.info(f"  📡 RSSI: {payload_summary.get('rssi', 'N/A')} dBm, SNR: {payload_summary.get('snr', 'N/A')} dB")
        
        # 디코딩된 데이터 표시
        decoded_data = payload_summary.get('decoded_data', {})
        if 'text' in decoded_data:
            self.logger.info(f"  📝 텍스트: '{decoded_data['text']}'")
        if 'hex' in decoded_data:
            self.logger.info(f"  📊 HEX: {decoded_data['hex']} (크기: {payload_summary.get('data_size', 0)} bytes)")
        
        self.logger.info(f"  🔢 Frame Count: {payload_summary.get('fCnt', 'N/A')}, Port: {payload_summary.get('fPort', 'N/A')}")
        
        # 원본 Base64 데이터는 debug 레벨로
        self.logger.debug(f"  📦 Base64: {payload_summary.get('data', 'N/A')}")
    
    def _log_join_info(self, application_id: str, device_id: str, join_summary: Dict):
        """JOIN 이벤트 정보 로깅"""
        self.logger.info(f"🔗 LoRa JOIN 이벤트 수신 - App: {application_id}, Device: {device_id}")
        self.logger.info(f"  🆔 DevEUI: {join_summary.get('devEUI', 'N/A')}")
        self.logger.info(f"  🏷️  DevAddr: {join_summary.get('devAddr', 'N/A')}")
        self.logger.info(f"  📡 RSSI: {join_summary.get('rssi', 'N/A')} dBm, SNR: {join_summary.get('snr', 'N/A')} dB")
    
    def _save_uplink_data(self, payload_summary: Dict, application_id: str, 
                         device_id: str, topic: str, legacy_log_data: Dict):
        """업링크 데이터를 SQLite와 JSON 파일에 저장"""
        
        # 1. SQLite에 저장
        if self.db:
            try:
                uplink_message = UplinkMessage.from_payload_summary(
                    payload_summary, application_id, device_id, 
                    topic, socket.gethostname()
                )
                message_id = self.db.insert_uplink_message(uplink_message)
                if message_id:
                    self.stats['sqlite_saves'] += 1
                    self.logger.debug(f"SQLite 저장 완료 - ID: {message_id}")
                    
            except Exception as e:
                self.logger.error(f"SQLite 저장 오류: {e}")
        
        # 2. JSON 파일에 저장 (기존 방식 유지)
        self._log_uplink_to_json(legacy_log_data)
    
    def _save_join_event(self, join_summary: Dict, application_id: str, 
                        device_id: str, topic: str):
        """JOIN 이벤트를 SQLite와 JSON 파일에 저장"""
        
        # 1. SQLite에 저장
        if self.db:
            try:
                join_event = JoinEvent.from_payload_summary(
                    join_summary, application_id, device_id, 
                    topic, socket.gethostname()
                )
                event_id = self.db.insert_join_event(join_event)
                if event_id:
                    self.stats['sqlite_saves'] += 1
                    self.logger.debug(f"JOIN 이벤트 SQLite 저장 완료 - ID: {event_id}")
                    
            except Exception as e:
                self.logger.error(f"JOIN 이벤트 SQLite 저장 오류: {e}")
        
        # 2. JSON 파일에 저장 (선택적)
        kst = timezone(timedelta(hours=9))
        self._log_join_to_json({
            "timestamp": datetime.now(kst).isoformat(),
            "event_type": "join",
            "topic": topic,
            "application_id": application_id,
            "device_id": device_id,
            "join_summary": join_summary,
            "hostname": socket.gethostname()
        })
    
    def _log_uplink_to_json(self, data: Dict):
        """업링크 데이터를 JSON 파일에 저장"""
        kst = timezone(timedelta(hours=9))
        log_filename = f"uplink_data_{datetime.now(kst).strftime('%Y%m%d')}.json"
        
        try:
            with open(log_filename, 'a', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
                f.write('\n')
                self.stats['json_saves'] += 1
        except Exception as e:
            self.logger.error(f"JSON 데이터 저장 오류: {e}")
    
    def _log_join_to_json(self, data: Dict):
        """JOIN 이벤트를 JSON 파일에 저장"""
        kst = timezone(timedelta(hours=9))
        log_filename = f"join_events_{datetime.now(kst).strftime('%Y%m%d')}.json"
        
        try:
            with open(log_filename, 'a', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
                f.write('\n')
                self.stats['json_saves'] += 1
        except Exception as e:
            self.logger.error(f"JOIN 이벤트 JSON 저장 오류: {e}")
    
    def get_statistics(self) -> Dict:
        """현재 통계 정보 반환"""
        return self.stats.copy()
    
    def close(self):
        """리소스 정리"""
        if self.db:
            self.db.close()