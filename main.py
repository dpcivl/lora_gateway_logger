import paho.mqtt.client as mqtt
import json
import logging
from datetime import datetime
import os
import signal
import sys
import socket
import base64
from logging.handlers import RotatingFileHandler, SysLogHandler

# SQLite 연동 모듈
try:
    from database import LoRaDatabase
    from models import UplinkMessage
    SQLITE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"SQLite 모듈을 로드할 수 없습니다: {e}. JSON 로깅만 사용합니다.")
    SQLITE_AVAILABLE = False

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
    def __init__(self, broker_host="localhost", broker_port=1883, username=None, password=None, 
                 enable_sqlite=True, db_path="lora_gateway.db"):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.client = None
        self.topic_pattern = "application/+/device/+/event/up"
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
        
        # 디버깅을 위한 상태 정보
        self.stats = {
            'messages_received': 0,
            'messages_processed': 0,
            'sqlite_saves': 0,
            'json_saves': 0,
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
            
            # 디코딩된 데이터 표시
            decoded_data = payload_summary.get('decoded_data', {})
            if 'text' in decoded_data:
                self.logger.info(f"  📝 텍스트: '{decoded_data['text']}'")
            if 'hex' in decoded_data:
                self.logger.info(f"  📊 HEX: {decoded_data['hex']} (크기: {payload_summary.get('data_size', 0)} bytes)")
            
            self.logger.info(f"  🔢 Frame Count: {payload_summary.get('fCnt', 'N/A')}, Port: {payload_summary.get('fPort', 'N/A')}")
            
            # 원본 Base64 데이터는 debug 레벨로
            self.logger.debug(f"  📦 Base64: {payload_summary.get('data', 'N/A')}")
            
            # 데이터 저장 (SQLite + JSON 병행)
            self.save_uplink_data(payload_summary, application_id, device_id, msg.topic, log_data)
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
            
            # 데이터 페이로드 추출 및 디코딩
            if 'data' in payload:
                summary['data'] = payload['data']
                summary['decoded_data'] = self._decode_payload_data(payload['data'])
                # Base64 디코딩된 데이터의 실제 바이트 크기
                try:
                    decoded_bytes = base64.b64decode(payload['data'])
                    summary['data_size'] = len(decoded_bytes)
                except:
                    summary['data_size'] = len(payload['data']) // 2  # fallback to hex calculation
            
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
    
    def _decode_payload_data(self, data):
        """Base64 인코딩된 LoRa 페이로드 데이터 디코딩"""
        decoded_info = {}
        
        try:
            # Base64 디코딩
            decoded_bytes = base64.b64decode(data)
            
            # HEX 표현
            decoded_info['hex'] = decoded_bytes.hex().upper()
            
            # ASCII 텍스트로 변환 시도
            try:
                decoded_text = decoded_bytes.decode('utf-8')
                # 출력 가능한 문자인지 확인
                if decoded_text.isprintable():
                    decoded_info['text'] = decoded_text
                else:
                    decoded_info['text'] = f"[비출력문자포함: {repr(decoded_text)}]"
            except UnicodeDecodeError:
                decoded_info['text'] = "[텍스트 디코딩 불가]"
            
            # 바이트 배열도 표시 (디버깅용)
            decoded_info['bytes'] = list(decoded_bytes)
            
        except Exception as e:
            decoded_info = {
                'error': f"디코딩 오류: {e}",
                'raw': data
            }
            
        return decoded_info
    
    def save_uplink_data(self, payload_summary: dict, application_id: str, 
                        device_id: str, topic: str, legacy_log_data: dict):
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
        self.log_uplink_data(legacy_log_data)
    
    def log_uplink_data(self, data):
        log_filename = f"uplink_data_{datetime.now().strftime('%Y%m%d')}.json"
        
        try:
            with open(log_filename, 'a', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
                f.write('\n')
                self.stats['json_saves'] += 1
        except Exception as e:
            logging.error(f"JSON 데이터 저장 오류: {e}")
    
    def on_disconnect(self, client, userdata, rc):
        logging.info("MQTT 브로커 연결 해제")
    
    def print_stats(self):
        """디버깅을 위한 통계 정보 출력"""
        if self.stats['start_time']:
            uptime = datetime.now() - self.stats['start_time']
            sqlite_info = f"SQLite: {self.stats['sqlite_saves']}, " if self.db else ""
            self.logger.info(f"통계 - 가동시간: {uptime}, 수신: {self.stats['messages_received']}, "
                           f"처리: {self.stats['messages_processed']}, "
                           f"{sqlite_info}JSON: {self.stats['json_saves']}, "
                           f"오류: {self.stats['errors']}")
    
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