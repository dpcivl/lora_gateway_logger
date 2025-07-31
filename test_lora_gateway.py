import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import tempfile
import os
from datetime import datetime
import sys
sys.path.insert(0, os.path.dirname(__file__))

from main import LoRaGatewayLogger

class TestLoRaGatewayLogger(unittest.TestCase):
    def setUp(self):
        self.logger = LoRaGatewayLogger(
            broker_host="test-broker",
            broker_port=1883,
            username="test_user",
            password="test_pass"
        )
        
    def test_init(self):
        """로거 초기화 테스트"""
        self.assertEqual(self.logger.broker_host, "test-broker")
        self.assertEqual(self.logger.broker_port, 1883)
        self.assertEqual(self.logger.username, "test_user")
        self.assertEqual(self.logger.password, "test_pass")
        self.assertEqual(self.logger.topic_pattern, "application/+/device/+/event/up")
        
    @patch('main.logging')
    def test_on_connect_success(self, mock_logging):
        """MQTT 연결 성공 테스트"""
        mock_client = Mock()
        self.logger.on_connect(mock_client, None, None, 0)
        
        mock_client.subscribe.assert_called_once_with(self.logger.topic_pattern)
        self.assertEqual(mock_logging.info.call_count, 2)
        
    @patch('main.logging')
    def test_on_connect_failure(self, mock_logging):
        """MQTT 연결 실패 테스트"""
        mock_client = Mock()
        self.logger.on_connect(mock_client, None, None, 1)
        
        mock_client.subscribe.assert_not_called()
        mock_logging.error.assert_called_once()
        
    def test_on_message_valid_payload(self):
        """유효한 메시지 처리 테스트"""
        mock_client = Mock()
        mock_msg = Mock()
        mock_msg.topic = "application/123/device/456/event/up"
        payload_data = '{"data": "test_data", "rssi": -80}'
        mock_msg.payload = payload_data.encode('utf-8')  # 실제 bytes 객체로 설정
        
        with patch.object(self.logger, 'log_uplink_data') as mock_log:
            self.logger.on_message(mock_client, None, mock_msg)
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args[0][0]
            self.assertEqual(call_args['application_id'], '123')
            self.assertEqual(call_args['device_id'], '456')
            self.assertEqual(call_args['topic'], mock_msg.topic)
            
    def test_on_message_invalid_json(self):
        """잘못된 JSON 메시지 처리 테스트"""
        mock_client = Mock()
        mock_msg = Mock()
        mock_msg.topic = "application/123/device/456/event/up"
        mock_msg.payload = b'invalid json'  # 실제 bytes 객체로 설정
        
        with patch.object(self.logger.logger, 'error') as mock_error:
            self.logger.on_message(mock_client, None, mock_msg)
            mock_error.assert_called()
        
    def test_log_uplink_data(self):
        """업링크 데이터 로깅 테스트"""
        test_data = {
            "timestamp": datetime.now().isoformat(),
            "topic": "application/123/device/456/event/up",
            "application_id": "123",
            "device_id": "456",
            "payload": {"data": "test"}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_file:
            temp_filename = tmp_file.name
            
        try:
            with patch('main.datetime') as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "20240101"
                
                with patch('builtins.open', mock_open()) as mock_file:
                    self.logger.log_uplink_data(test_data)
                    mock_file.assert_called_once()
                    
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

def mock_open():
    """파일 open 모킹을 위한 헬퍼 함수"""
    mock_file = MagicMock()
    mock_file.__enter__.return_value = mock_file
    mock_file.__exit__.return_value = None
    return MagicMock(return_value=mock_file)

if __name__ == '__main__':
    unittest.main()