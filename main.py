import paho.mqtt.client as mqtt
import json
import logging
from datetime import datetime
import os
import signal
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('lora_gateway.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class LoRaGatewayLogger:
    def __init__(self, broker_host="localhost", broker_port=1883, username=None, password=None):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.client = None
        self.topic_pattern = "application/+/device/+/event/up"
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info(f"MQTT 브로커 연결 성공: {self.broker_host}:{self.broker_port}")
            client.subscribe(self.topic_pattern)
            logging.info(f"토픽 구독: {self.topic_pattern}")
        else:
            logging.error(f"MQTT 브로커 연결 실패, 오류 코드: {rc}")
    
    def on_message(self, client, userdata, msg):
        try:
            topic_parts = msg.topic.split('/')
            application_id = topic_parts[1]
            device_id = topic_parts[3]
            
            payload = json.loads(msg.payload.decode('utf-8'))
            
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "topic": msg.topic,
                "application_id": application_id,
                "device_id": device_id,
                "payload": payload
            }
            
            logging.info(f"LoRa 업링크 데이터 수신 - App: {application_id}, Device: {device_id}")
            self.log_uplink_data(log_data)
            
        except json.JSONDecodeError as e:
            logging.error(f"JSON 파싱 오류: {e}")
        except Exception as e:
            logging.error(f"메시지 처리 오류: {e}")
    
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
    
    def start(self):
        try:
            self.client = mqtt.Client()
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.on_disconnect = self.on_disconnect
            
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)
            
            logging.info(f"MQTT 브로커 연결 시도: {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, 60)
            
            self.client.loop_forever()
            
        except KeyboardInterrupt:
            logging.info("사용자 중단 요청")
        except Exception as e:
            logging.error(f"오류: {e}")
        finally:
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