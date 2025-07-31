#!/usr/bin/env python3
"""
통합 테스트 스크립트
실제 MQTT 브로커를 사용하여 전체 시스템을 테스트합니다.
"""

import subprocess
import time
import json
import logging
import threading
from mock_mqtt_publisher import MockLoRaDataPublisher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntegrationTest:
    def __init__(self, broker_host="127.0.0.1", broker_port=1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.publisher = MockLoRaDataPublisher(broker_host, broker_port)
        self.logger_process = None
        
    def start_mqtt_broker(self):
        """Docker를 사용하여 MQTT 브로커 시작"""
        try:
            # 기존 컨테이너 확인
            result = subprocess.run([
                "docker", "ps", "-q", "-f", "name=test-mosquitto"
            ], capture_output=True, text=True)
            
            if result.stdout.strip():
                logger.info("기존 MQTT 브로커 컨테이너 사용")
                return True
                
            # 중지된 컨테이너 확인 및 제거
            result = subprocess.run([
                "docker", "ps", "-aq", "-f", "name=test-mosquitto"
            ], capture_output=True, text=True)
            
            if result.stdout.strip():
                logger.info("기존 컨테이너 제거 후 재시작...")
                subprocess.run(["docker", "rm", "-f", "test-mosquitto"], check=True)
            
            logger.info("새로운 MQTT 브로커 시작...")
            subprocess.run([
                "docker", "run", "-d", "--name", "test-mosquitto", 
                "-p", "1883:1883", "-p", "9001:9001",
                "eclipse-mosquitto:2.0"
            ], check=True)
            time.sleep(5)  # 브로커가 시작될 때까지 대기
            logger.info("MQTT 브로커가 시작됨")
            return True
        except subprocess.CalledProcessError as e:
            logger.warning(f"Docker 브로커 시작 실패: {e}")
            return False
            
    def stop_mqtt_broker(self):
        """테스트용 MQTT 브로커 중지"""
        try:
            subprocess.run(["docker", "stop", "test-mosquitto"], check=True)
            subprocess.run(["docker", "rm", "test-mosquitto"], check=True)
            logger.info("MQTT 브로커 중지됨")
        except subprocess.CalledProcessError:
            pass
            
    def start_logger(self):
        """LoRa Gateway Logger 시작"""
        logger.info("LoRa Gateway Logger 시작...")
        self.logger_process = subprocess.Popen([
            "python", "main.py"
        ], env={
            "MQTT_BROKER_HOST": self.broker_host,
            "MQTT_BROKER_PORT": str(self.broker_port),
            "LOG_LEVEL": "DEBUG"
        })
        time.sleep(5)  # 로거가 시작될 때까지 대기
        
    def stop_logger(self):
        """LoRa Gateway Logger 중지"""
        if self.logger_process:
            self.logger_process.terminate()
            self.logger_process.wait(timeout=10)
            logger.info("LoRa Gateway Logger 중지됨")
            
    def run_test_scenario(self):
        """테스트 시나리오 실행"""
        logger.info("=== 통합 테스트 시작 ===")
        
        try:
            # 1. MQTT 브로커 시작
            self.start_mqtt_broker()
            
            # 2. Logger 시작
            self.start_logger()
            
            # 3. 테스트 데이터 발행
            logger.info("테스트 데이터 발행...")
            self.publisher.publish_mock_data(
                application_id="test-app-123",
                device_id="test-device-456", 
                count=10,
                interval=2
            )
            
            # 4. 로그 파일 확인
            time.sleep(10)
            self.verify_logs()
            
            logger.info("=== 통합 테스트 완료 ===")
            
        except Exception as e:
            logger.error(f"통합 테스트 실패: {e}")
            raise
        finally:
            self.stop_logger()
            self.stop_mqtt_broker()
            
    def verify_logs(self):
        """로그 파일 검증"""
        import os
        import glob
        
        # 업링크 데이터 파일 확인
        uplink_files = glob.glob("uplink_data_*.json")
        if not uplink_files:
            raise AssertionError("업링크 데이터 파일이 생성되지 않음")
            
        logger.info(f"생성된 업링크 파일: {uplink_files}")
        
        # 파일 내용 검증
        with open(uplink_files[0], 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if len(lines) == 0:
                raise AssertionError("업링크 데이터가 기록되지 않음")
                
            # 첫 번째 라인 JSON 파싱 테스트
            data = json.loads(lines[0])
            required_fields = ['timestamp', 'topic', 'application_id', 'device_id', 'payload']
            for field in required_fields:
                if field not in data:
                    raise AssertionError(f"필수 필드 누락: {field}")
                    
        logger.info(f"업링크 데이터 검증 완료: {len(lines)}개 레코드")
        
        # 로그 파일 확인
        if os.path.exists("lora_gateway.log"):
            with open("lora_gateway.log", 'r', encoding='utf-8') as f:
                log_content = f.read()
                if "MQTT 브로커 연결 성공" not in log_content:
                    raise AssertionError("MQTT 연결 로그 누락")
                if "LoRa 업링크 데이터 수신" not in log_content:
                    raise AssertionError("데이터 수신 로그 누락")
                    
        logger.info("로그 파일 검증 완료")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='LoRa Gateway Logger 통합 테스트')
    parser.add_argument('--broker', default='127.0.0.1', help='MQTT 브로커 호스트')
    parser.add_argument('--port', type=int, default=1883, help='MQTT 브로커 포트')
    
    args = parser.parse_args()
    
    test = IntegrationTest(args.broker, args.port)
    test.run_test_scenario()