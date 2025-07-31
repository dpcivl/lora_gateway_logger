import logging
import signal
import sys
import threading
import time
from datetime import datetime

from config import load_config_from_env, setup_logging
from core.mqtt_client import LoRaMQTTClient
from core.message_parser import LoRaMessageParser
from core.data_processor import LoRaDataProcessor

class LoRaGatewayLogger:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 핵심 컴포넌트 초기화
        self.mqtt_client = LoRaMQTTClient(
            broker_host=config.mqtt.broker_host,
            broker_port=config.mqtt.broker_port,
            username=config.mqtt.username,
            password=config.mqtt.password
        )
        
        self.message_parser = LoRaMessageParser()
        
        self.data_processor = LoRaDataProcessor(
            enable_sqlite=config.database.enable_sqlite,
            db_path=config.database.db_path
        )
        
        # MQTT 콜백 설정
        self.mqtt_client.set_message_callback(self._on_message)
        
        # 통계 정보
        self.stats = {
            'start_time': None,
            'errors': 0
        }
        
    def _on_message(self, client, userdata, msg):
        """MQTT 메시지 수신 처리"""
        try:
            # 토픽 파싱
            topic_info = self.message_parser.parse_topic(msg.topic)
            if not topic_info:
                return
            
            application_id, device_id, event_type = topic_info
            
            # 페이로드 파싱
            payload = self.message_parser.parse_payload(msg.payload)
            if not payload:
                return
            
            # 이벤트 유형별 처리
            if event_type == 'up':
                self._handle_uplink_message(application_id, device_id, msg.topic, payload)
            elif event_type == 'join':
                self._handle_join_event(application_id, device_id, msg.topic, payload)
            else:
                self.logger.warning(f"알 수 없는 이벤트 유형: {event_type} (토픽: {msg.topic})")
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"메시지 처리 오류: {e} - Topic: {msg.topic}", exc_info=True)
    
    def _handle_uplink_message(self, application_id: str, device_id: str, topic: str, payload: dict):
        """업링크 메시지 처리"""
        payload_summary = self.message_parser.extract_uplink_summary(payload)
        self.data_processor.process_uplink_message(application_id, device_id, topic, payload_summary)
    
    def _handle_join_event(self, application_id: str, device_id: str, topic: str, payload: dict):
        """JOIN 이벤트 처리"""
        join_summary = self.message_parser.extract_join_summary(payload)
        self.data_processor.process_join_event(application_id, device_id, topic, join_summary)
    
    
    
    
    
    
    
    
    
    
    
    def print_stats(self):
        """디버깅을 위한 통계 정보 출력"""
        if self.stats['start_time']:
            uptime = datetime.now() - self.stats['start_time']
            processor_stats = self.data_processor.get_statistics()
            
            self.logger.info(f"통계 - 가동시간: {uptime}, "
                           f"업링크: {processor_stats['messages_received']}/{processor_stats['messages_processed']}, "
                           f"JOIN: {processor_stats['joins_received']}/{processor_stats['joins_processed']}, "
                           f"SQLite: {processor_stats['sqlite_saves']}, JSON: {processor_stats['json_saves']}, "
                           f"오류: {self.stats['errors']}")
    
    def start(self):
        """LoRa Gateway Logger 시작"""
        try:
            self.stats['start_time'] = datetime.now()
            
            # MQTT 클라이언트 연결
            if not self.mqtt_client.connect(max_retries=self.config.mqtt.connection_retries):
                raise RuntimeError("MQTT 브로커 연결 실패")
            
            # 주기적으로 통계 출력 (별도 스레드)
            def stats_reporter():
                while True:
                    time.sleep(self.config.stats_interval)
                    if self.mqtt_client.is_connected():
                        self.print_stats()
            
            stats_thread = threading.Thread(target=stats_reporter, daemon=True)
            stats_thread.start()
            
            # MQTT 메시지 루프 시작 (블로킹)
            self.mqtt_client.start_loop()
            
        except KeyboardInterrupt:
            self.logger.info("사용자 중단 요청")
        except Exception as e:
            self.logger.error(f"오류: {e}", exc_info=True)
        finally:
            self.print_stats()
            self.stop()
    
    def stop(self):
        """LoRa Gateway Logger 중지"""
        self.mqtt_client.stop()
        self.data_processor.close()

def signal_handler(sig, frame):
    logging.info('프로그램을 종료합니다')
    sys.exit(0)

if __name__ == "__main__":
    # 설정 로드
    config = load_config_from_env()
    
    # 로깅 설정
    setup_logging(config.logging)
    
    # 시그널 핸들러 설정
    signal.signal(signal.SIGINT, signal_handler)
    
    # 로거 초기화 및 시작
    logger = LoRaGatewayLogger(config)
    
    logging.info("LoRa 게이트웨이 로거 시작")
    logger.start()