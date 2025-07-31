import paho.mqtt.client as mqtt
import json
import logging
from datetime import datetime
import os
import signal
import sys
import socket
from logging.handlers import RotatingFileHandler, SysLogHandler

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 로깅 설정을 더 상세하게 구성
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
log_handlers = []

# 파일 로깅 (로테이션 지원)
file_handler = RotatingFileHandler(
    'lora_gateway.log', 
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
log_handlers.append(file_handler)

# 콘솔 로깅
console_handler = logging.StreamHandler()
log_handlers.append(console_handler)

# 원격 syslog 지원 (라즈베리파이에서 PC로 로그 전송)
if os.getenv('SYSLOG_HOST'):
    try:
        syslog_handler = SysLogHandler(
            address=(os.getenv('SYSLOG_HOST'), int(os.getenv('SYSLOG_PORT', '514')))
        )
        syslog_handler.setFormatter(logging.Formatter(
            f'{socket.gethostname()} lora-gateway: %(levelname)s - %(message)s'
        ))
        log_handlers.append(syslog_handler)
    except Exception as e:
        print(f"Syslog 설정 실패: {e}")

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=log_handlers
)

class LoRaGatewayLogger:
    def __init__(self, broker_host="localhost", broker_port=1883, username=None, password=None):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.client = None
        self.topic_pattern = "application/+/device/+/event/up"
        self.logger = logging.getLogger(__name__)
        
        # 디버깅을 위한 상태 정보
        self.stats = {
            'messages_received': 0,
            'messages_processed': 0,
            'errors': 0,
            'start_time': None,
            'last_message_time': None
        }
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info(f"MQTT 브로커 연결 성공: {self.broker_host}:{self.broker_port}")
            client.subscribe(self.topic_pattern)
            logging.info(f"토픽 구독: {self.topic_pattern}")
        else:
            logging.error(f"MQTT 브로커 연결 실패, 오류 코드: {rc}")
    
    def on_message(self, client, userdata, msg):
        try:
            self.stats['messages_received'] += 1
            self.stats['last_message_time'] = datetime.now()
            
            self.logger.debug(f"메시지 수신: {msg.topic} - 크기: {len(msg.payload)} bytes")
            
            topic_parts = msg.topic.split('/')
            application_id = topic_parts[1]
            device_id = topic_parts[3]
            
            payload = json.loads(msg.payload.decode('utf-8'))
            
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "topic": msg.topic,
                "application_id": application_id,
                "device_id": device_id,
                "payload": payload,
                "raw_payload_size": len(msg.payload),
                "hostname": socket.gethostname()
            }
            
            # 페이로드 주요 정보 추출 및 로깅
            payload_summary = self._extract_payload_summary(payload)
            self.logger.info(f"LoRa 업링크 데이터 수신 - App: {application_id}, Device: {device_id}")
            self.logger.info(f"  📡 RSSI: {payload_summary.get('rssi', 'N/A')} dBm, SNR: {payload_summary.get('snr', 'N/A')} dB")
            self.logger.info(f"  📊 Data: {payload_summary.get('data', 'N/A')} (크기: {payload_summary.get('data_size', 0)} bytes)")
            self.logger.info(f"  🔢 Frame Count: {payload_summary.get('fCnt', 'N/A')}, Port: {payload_summary.get('fPort', 'N/A')}")
            
            self.log_uplink_data(log_data)
            self.stats['messages_processed'] += 1
            
        except json.JSONDecodeError as e:
            self.stats['errors'] += 1
            self.logger.error(f"JSON 파싱 오류: {e} - Raw payload: {msg.payload}")
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"메시지 처리 오류: {e} - Topic: {msg.topic}", exc_info=True)
    
    def _extract_payload_summary(self, payload):
        """LoRa 페이로드에서 주요 정보 추출 (SQLite 연동 준비)"""
        summary = {}
        
        try:
            # RSSI와 SNR 추출 (첫 번째 게이트웨이 기준)
            if 'rxInfo' in payload and len(payload['rxInfo']) > 0:
                rx_info = payload['rxInfo'][0]
                summary['rssi'] = rx_info.get('rssi')
                summary['snr'] = rx_info.get('loRaSNR')
                
                # 위치 정보도 추출
                if 'location' in rx_info:
                    summary['latitude'] = rx_info['location'].get('latitude')
                    summary['longitude'] = rx_info['location'].get('longitude')
            
            # 데이터 페이로드 추출
            if 'data' in payload:
                summary['data'] = payload['data']
                summary['data_size'] = len(payload['data']) // 2  # hex string의 실제 바이트 크기
            
            # 프레임 정보 추출
            summary['fCnt'] = payload.get('fCnt')
            summary['fPort'] = payload.get('fPort')
            summary['devEUI'] = payload.get('devEUI')
            
            # 전송 정보 추출
            if 'txInfo' in payload:
                tx_info = payload['txInfo']
                summary['frequency'] = tx_info.get('frequency')
                summary['dataRate'] = tx_info.get('dr')
                
        except Exception as e:
            self.logger.debug(f"페이로드 정보 추출 오류: {e}")
            
        return summary
    
    def log_uplink_data(self, data):
        log_filename = f"uplink_data_{datetime.now().strftime('%Y%m%d')}.json"
        
        try:
            with open(log_filename, 'a', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
                f.write('\n')
        except Exception as e:
            logging.error(f"데이터 저장 오류: {e}")
    
    def on_disconnect(self, client, userdata, rc):
        logging.info("MQTT 브로커 연결 해제")
    
    def print_stats(self):
        """디버깅을 위한 통계 정보 출력"""
        if self.stats['start_time']:
            uptime = datetime.now() - self.stats['start_time']
            self.logger.info(f"통계 - 가동시간: {uptime}, 수신: {self.stats['messages_received']}, "
                           f"처리: {self.stats['messages_processed']}, 오류: {self.stats['errors']}")
    
    def start(self):
        try:
            self.stats['start_time'] = datetime.now()
            
            self.client = mqtt.Client()
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.on_disconnect = self.on_disconnect
            
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)
            
            # Windows 네트워크 스택 문제 해결 시도
            import time
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.logger.info(f"MQTT 브로커 연결 시도 {attempt + 1}/{max_retries}: {self.broker_host}:{self.broker_port}")
                    self.client.connect(self.broker_host, self.broker_port, 60)
                    break
                except (OSError, socket.error) as e:
                    if attempt < max_retries - 1:
                        self.logger.warning(f"연결 실패 (시도 {attempt + 1}): {e}, 2초 후 재시도...")
                        time.sleep(2)
                    else:
                        raise
            
            # 주기적으로 통계 출력 (별도 스레드)
            import threading
            def stats_reporter():
                while True:
                    import time
                    time.sleep(300)  # 5분마다
                    if self.client and self.client.is_connected():
                        self.print_stats()
            
            stats_thread = threading.Thread(target=stats_reporter, daemon=True)
            stats_thread.start()
            
            self.client.loop_forever()
            
        except KeyboardInterrupt:
            self.logger.info("사용자 중단 요청")
        except Exception as e:
            self.logger.error(f"오류: {e}", exc_info=True)
        finally:
            self.print_stats()
            if self.client:
                self.client.disconnect()
    
    def stop(self):
        if self.client:
            self.client.disconnect()

def signal_handler(sig, frame):
    logging.info('프로그램을 종료합니다')
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    
    broker_host = os.getenv('MQTT_BROKER_HOST', 'localhost')
    broker_port = int(os.getenv('MQTT_BROKER_PORT', '1883'))
    username = os.getenv('MQTT_USERNAME')
    password = os.getenv('MQTT_PASSWORD')
    
    logger = LoRaGatewayLogger(
        broker_host=broker_host,
        broker_port=broker_port,
        username=username,
        password=password
    )
    
    logging.info("LoRa 게이트웨이 로거 시작")
    logger.start()