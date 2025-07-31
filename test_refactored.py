"""
리팩터링된 구조에 대한 단위 테스트
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime

from core.message_parser import LoRaMessageParser
from core.data_processor import LoRaDataProcessor
from core.mqtt_client import LoRaMQTTClient
from config import MQTTConfig, DatabaseConfig, LoggingConfig, AppConfig


class TestMessageParser(unittest.TestCase):
    def setUp(self):
        self.parser = LoRaMessageParser()
    
    def test_parse_topic_valid(self):
        """유효한 토픽 파싱 테스트"""
        topic = "application/test-app/device/test-device/event/up"
        result = self.parser.parse_topic(topic)
        
        self.assertIsNotNone(result)
        app_id, device_id, event_type = result
        self.assertEqual(app_id, "test-app")
        self.assertEqual(device_id, "test-device")
        self.assertEqual(event_type, "up")
    
    def test_parse_topic_invalid(self):
        """잘못된 토픽 파싱 테스트"""
        topic = "invalid/topic"
        result = self.parser.parse_topic(topic)
        self.assertIsNone(result)
    
    def test_parse_payload_valid_json(self):
        """유효한 JSON 페이로드 파싱 테스트"""
        payload_data = {"test": "data", "value": 123}
        payload_bytes = json.dumps(payload_data).encode('utf-8')
        
        result = self.parser.parse_payload(payload_bytes)
        self.assertEqual(result, payload_data)
    
    def test_parse_payload_invalid_json(self):
        """잘못된 JSON 페이로드 파싱 테스트"""
        payload_bytes = b'invalid json'
        result = self.parser.parse_payload(payload_bytes)
        self.assertIsNone(result)
    
    def test_extract_uplink_summary(self):
        """업링크 페이로드 요약 추출 테스트"""
        payload = {
            "rxInfo": [{
                "rssi": -85,
                "loRaSNR": 7.2,
                "location": {"latitude": 37.5665, "longitude": 126.9780}
            }],
            "data": "VEVTVA==",  # "TEST" in Base64
            "fCnt": 42,
            "fPort": 1,
            "devEUI": "0102030405060708",
            "txInfo": {"frequency": 868100000, "dr": 5}
        }
        
        summary = self.parser.extract_uplink_summary(payload)
        
        self.assertEqual(summary['rssi'], -85)
        self.assertEqual(summary['snr'], 7.2)
        self.assertEqual(summary['data'], "VEVTVA==")
        self.assertEqual(summary['fCnt'], 42)
        self.assertEqual(summary['devEUI'], "0102030405060708")
        self.assertIn('decoded_data', summary)
        self.assertEqual(summary['decoded_data']['text'], 'TEST')
    
    def test_extract_join_summary(self):
        """JOIN 이벤트 요약 추출 테스트"""
        payload = {
            "devEUI": "0102030405060708",
            "joinEUI": "0807060504030201",
            "devAddr": "12345678",
            "rxInfo": [{
                "rssi": -90,
                "loRaSNR": 5.5
            }],
            "txInfo": {"frequency": 868300000, "dr": 0}
        }
        
        summary = self.parser.extract_join_summary(payload)
        
        self.assertEqual(summary['devEUI'], "0102030405060708")
        self.assertEqual(summary['joinEUI'], "0807060504030201")
        self.assertEqual(summary['devAddr'], "12345678")
        self.assertEqual(summary['rssi'], -90)
        self.assertEqual(summary['snr'], 5.5)


class TestDataProcessor(unittest.TestCase):
    def setUp(self):
        # SQLite 없이 테스트 (JSON만)
        self.processor = LoRaDataProcessor(enable_sqlite=False)
    
    @patch('builtins.open', create=True)
    @patch('json.dump')
    def test_process_uplink_message(self, mock_json_dump, mock_open):
        """업링크 메시지 처리 테스트"""
        payload_summary = {
            'rssi': -85,
            'snr': 7.2,
            'decoded_data': {'text': 'TEST', 'hex': '54455354'},
            'fCnt': 42
        }
        
        self.processor.process_uplink_message(
            "test-app", "test-device", "test/topic", payload_summary
        )
        
        # 통계 확인
        stats = self.processor.get_statistics()
        self.assertEqual(stats['messages_received'], 1)
        self.assertEqual(stats['messages_processed'], 1)
        
        # JSON 파일 저장 확인
        mock_open.assert_called()
        mock_json_dump.assert_called()
    
    @patch('builtins.open', create=True)
    @patch('json.dump')
    def test_process_join_event(self, mock_json_dump, mock_open):
        """JOIN 이벤트 처리 테스트"""
        join_summary = {
            'devEUI': '0102030405060708',
            'devAddr': '12345678',
            'rssi': -90
        }
        
        self.processor.process_join_event(
            "test-app", "test-device", "test/topic", join_summary
        )
        
        # 통계 확인
        stats = self.processor.get_statistics()
        self.assertEqual(stats['joins_received'], 1)
        self.assertEqual(stats['joins_processed'], 1)


class TestMQTTClient(unittest.TestCase):
    def setUp(self):
        self.mqtt_client = LoRaMQTTClient("localhost", 1883)
    
    def test_initialization(self):
        """MQTT 클라이언트 초기화 테스트"""
        self.assertEqual(self.mqtt_client.broker_host, "localhost")
        self.assertEqual(self.mqtt_client.broker_port, 1883)
        self.assertIsNone(self.mqtt_client.client)
    
    def test_callback_setting(self):
        """콜백 함수 설정 테스트"""
        mock_callback = Mock()
        self.mqtt_client.set_message_callback(mock_callback)
        self.assertEqual(self.mqtt_client.on_message_callback, mock_callback)
    
    @patch('paho.mqtt.client.Client')
    def test_connect_success(self, mock_client_class):
        """MQTT 연결 성공 테스트"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        result = self.mqtt_client.connect()
        
        self.assertTrue(result)
        mock_client.connect.assert_called_once()
        mock_client_class.assert_called_once()


class TestConfig(unittest.TestCase):
    def test_config_creation(self):
        """설정 객체 생성 테스트"""
        mqtt_config = MQTTConfig(broker_host="test-broker", broker_port=8883)
        db_config = DatabaseConfig(enable_sqlite=False)
        log_config = LoggingConfig(log_level="DEBUG")
        
        app_config = AppConfig(
            mqtt=mqtt_config,
            database=db_config,
            logging=log_config
        )
        
        self.assertEqual(app_config.mqtt.broker_host, "test-broker")
        self.assertEqual(app_config.mqtt.broker_port, 8883)
        self.assertFalse(app_config.database.enable_sqlite)
        self.assertEqual(app_config.logging.log_level, "DEBUG")
    
    @patch.dict('os.environ', {
        'MQTT_BROKER_HOST': 'env-broker',
        'MQTT_BROKER_PORT': '8883',
        'LOG_LEVEL': 'DEBUG'
    })
    def test_load_config_from_env(self):
        """환경 변수에서 설정 로드 테스트"""
        from config import load_config_from_env
        
        config = load_config_from_env()
        
        self.assertEqual(config.mqtt.broker_host, 'env-broker')
        self.assertEqual(config.mqtt.broker_port, 8883)
        self.assertEqual(config.logging.log_level, 'DEBUG')


if __name__ == '__main__':
    unittest.main()