import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime

class MockLoRaDataPublisher:
    """실제 LoRa 데이터를 시뮬레이션하는 MQTT 퍼블리셔"""
    
    def __init__(self, broker_host="localhost", broker_port=1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client = mqtt.Client()
        
    def generate_mock_payload(self):
        """실제 LoRa 페이로드와 유사한 모킹 데이터 생성"""
        return {
            "applicationID": "1",
            "applicationName": "test-app",
            "deviceName": f"test-device-{random.randint(1, 5)}",
            "devEUI": f"{''.join([format(random.randint(0, 255), '02x') for _ in range(8)])}",
            "rxInfo": [{
                "gatewayID": "test-gateway",
                "rssi": random.randint(-120, -50),
                "loRaSNR": random.uniform(-20, 10),
                "location": {
                    "latitude": 37.5665 + random.uniform(-0.01, 0.01),
                    "longitude": 126.9780 + random.uniform(-0.01, 0.01)
                }
            }],
            "txInfo": {
                "frequency": 922100000,
                "dr": 5
            },
            "fCnt": random.randint(1, 1000),
            "fPort": 1,
            "data": f"{''.join([format(random.randint(0, 255), '02x') for _ in range(random.randint(4, 20))])}"
        }
    
    def publish_mock_data(self, application_id="123", device_id="456", count=1, interval=1):
        """모킹 데이터를 MQTT로 발행"""
        try:
            self.client.connect(self.broker_host, self.broker_port, 60)
            print(f"MQTT 브로커에 연결됨: {self.broker_host}:{self.broker_port}")
            
            for i in range(count):
                topic = f"application/{application_id}/device/{device_id}/event/up"
                payload = self.generate_mock_payload()
                
                self.client.publish(topic, json.dumps(payload))
                print(f"[{i+1}/{count}] 데이터 발행: {topic}")
                print(f"Payload: {json.dumps(payload, indent=2)}")
                
                if i < count - 1:
                    time.sleep(interval)
                    
        except Exception as e:
            print(f"오류 발생: {e}")
        finally:
            self.client.disconnect()
            print("MQTT 연결 종료")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='LoRa 데이터 모킹 퍼블리셔')
    parser.add_argument('--broker', default='localhost', help='MQTT 브로커 호스트')
    parser.add_argument('--port', type=int, default=1883, help='MQTT 브로커 포트')
    parser.add_argument('--app-id', default='123', help='애플리케이션 ID')
    parser.add_argument('--device-id', default='456', help='디바이스 ID')
    parser.add_argument('--count', type=int, default=5, help='발행할 메시지 수')
    parser.add_argument('--interval', type=float, default=2.0, help='메시지 간격(초)')
    
    args = parser.parse_args()
    
    publisher = MockLoRaDataPublisher(args.broker, args.port)
    publisher.publish_mock_data(
        application_id=args.app_id,
        device_id=args.device_id,
        count=args.count,
        interval=args.interval
    )