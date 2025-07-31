"""
SQLite 연동 기능 테스트
"""
import unittest
import tempfile
import os
from datetime import datetime
from models import UplinkMessage
from database import LoRaDatabase


class TestSQLiteIntegration(unittest.TestCase):
    def setUp(self):
        # 임시 데이터베이스 파일 생성
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = LoRaDatabase(self.temp_db.name)
    
    def tearDown(self):
        # 데이터베이스 연결 완전히 종료
        if hasattr(self, 'db'):
            self.db.close()
            del self.db
        
        # 잠시 대기 후 파일 삭제 (Windows SQLite 파일 잠금 해제)
        import time
        time.sleep(0.1)
        
        # 임시 파일 정리 (Windows 권한 문제 해결)
        try:
            if os.path.exists(self.temp_db.name):
                os.unlink(self.temp_db.name)
        except PermissionError:
            # Windows에서 파일이 잠겨있을 때 - 나중에 정리됨
            pass
    
    def test_database_initialization(self):
        """데이터베이스 초기화 테스트"""
        # 데이터베이스가 정상적으로 초기화되었는지 확인
        self.assertIsNotNone(self.db)
        
        # 테이블이 생성되었는지 확인
        stats = self.db.get_statistics()
        self.assertEqual(stats['total_messages'], 0)
    
    def test_uplink_message_creation(self):
        """UplinkMessage 생성 테스트"""
        # 샘플 페이로드 요약 데이터
        payload_summary = {
            'rssi': -85,
            'snr': 7.2,
            'decoded_data': {
                'hex': '54455354',
                'text': 'TEST'
            },
            'data': 'VEVTVA==',  # TEST의 Base64
            'data_size': 4,
            'fCnt': 42,
            'fPort': 1,
            'devEUI': '0102030405060708',
            'frequency': 868100000,
            'dataRate': 5,
            'latitude': 37.5665,
            'longitude': 126.9780
        }
        
        message = UplinkMessage.from_payload_summary(
            payload_summary, 'test-app', 'test-device', 
            'application/test-app/device/test-device/event/up', 'test-host'
        )
        
        # 필수 필드 확인
        self.assertEqual(message.application_id, 'test-app')
        self.assertEqual(message.device_id, 'test-device')
        self.assertEqual(message.payload_text, 'TEST')
        self.assertEqual(message.frame_count, 42)
        self.assertEqual(message.rssi, -85)
    
    def test_insert_and_retrieve(self):
        """데이터 삽입 및 조회 테스트"""
        # 테스트 메시지 생성
        message = UplinkMessage(
            timestamp=datetime.now(),
            application_id='test-app',
            device_id='test-device-001',
            payload_text='Hello World',
            payload_hex='48656C6C6F20576F726C64',
            frame_count=123,
            rssi=-90,
            snr=5.5
        )
        
        # 삽입
        message_id = self.db.insert_uplink_message(message)
        self.assertIsNotNone(message_id)
        self.assertIsInstance(message_id, int)
        
        # 조회
        messages = self.db.get_recent_messages(10)
        self.assertEqual(len(messages), 1)
        
        retrieved = messages[0]
        self.assertEqual(retrieved.application_id, 'test-app')
        self.assertEqual(retrieved.device_id, 'test-device-001')
        self.assertEqual(retrieved.payload_text, 'Hello World')
        self.assertEqual(retrieved.frame_count, 123)
    
    def test_device_messages(self):
        """디바이스별 메시지 조회 테스트"""
        # 여러 디바이스 메시지 생성
        devices = ['device-001', 'device-002', 'device-001']
        
        for i, device in enumerate(devices):
            message = UplinkMessage(
                timestamp=datetime.now(),
                application_id='test-app',
                device_id=device,
                payload_text=f'Message {i}',
                frame_count=i
            )
            self.db.insert_uplink_message(message)
        
        # device-001 메시지만 조회
        device_messages = self.db.get_device_messages('device-001')
        self.assertEqual(len(device_messages), 2)
        
        # 최신 메시지가 먼저 오는지 확인 (DESC 정렬)
        self.assertEqual(device_messages[0].payload_text, 'Message 2')
        self.assertEqual(device_messages[1].payload_text, 'Message 0')
    
    def test_statistics(self):
        """통계 정보 테스트"""
        # 초기 통계
        stats = self.db.get_statistics()
        self.assertEqual(stats['total_messages'], 0)
        self.assertEqual(stats['unique_devices'], 0)
        
        # 메시지 추가
        for i in range(3):
            message = UplinkMessage(
                timestamp=datetime.now(),
                application_id=f'app-{i % 2}',  # app-0, app-1, app-0
                device_id=f'device-{i}',
                payload_text=f'Test {i}'
            )
            self.db.insert_uplink_message(message)
        
        # 통계 확인
        stats = self.db.get_statistics()
        self.assertEqual(stats['total_messages'], 3)
        self.assertEqual(stats['unique_devices'], 3)
        self.assertEqual(stats['unique_applications'], 2)


if __name__ == '__main__':
    unittest.main()