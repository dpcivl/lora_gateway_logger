"""
MQTT 클라이언트 관리 모듈
MQTT 연결, 구독, 메시지 수신 처리
"""
import paho.mqtt.client as mqtt
import logging
import socket
import time
from typing import Callable, Optional


class LoRaMQTTClient:
    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883, 
                 username: Optional[str] = None, password: Optional[str] = None):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.client = None
        self.logger = logging.getLogger(__name__)
        
        # 토픽 패턴
        self.uplink_topic_pattern = "application/+/device/+/event/up"
        self.join_topic_pattern = "application/+/device/+/event/join"
        
        # 콜백 함수들
        self.on_message_callback: Optional[Callable] = None
        self.on_connect_callback: Optional[Callable] = None
        self.on_disconnect_callback: Optional[Callable] = None
    
    def set_message_callback(self, callback: Callable):
        """메시지 수신 콜백 설정"""
        self.on_message_callback = callback
    
    def set_connect_callback(self, callback: Callable):
        """연결 콜백 설정"""
        self.on_connect_callback = callback
    
    def set_disconnect_callback(self, callback: Callable):
        """연결 해제 콜백 설정"""
        self.on_disconnect_callback = callback
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT 브로커 연결 콜백"""
        if rc == 0:
            self.logger.info(f"MQTT 브로커 연결 성공: {self.broker_host}:{self.broker_port}")
            
            # 업링크 메시지 구독
            client.subscribe(self.uplink_topic_pattern)
            self.logger.info(f"업링크 토픽 구독: {self.uplink_topic_pattern}")
            
            # JOIN 이벤트 구독
            client.subscribe(self.join_topic_pattern)
            self.logger.info(f"JOIN 토픽 구독: {self.join_topic_pattern}")
            
            # 외부 콜백 호출
            if self.on_connect_callback:
                self.on_connect_callback(client, userdata, flags, rc)
        else:
            self.logger.error(f"MQTT 브로커 연결 실패, 오류 코드: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """MQTT 메시지 수신 콜백"""
        self.logger.debug(f"메시지 수신: {msg.topic} - 크기: {len(msg.payload)} bytes")
        
        # 외부 콜백으로 메시지 전달
        if self.on_message_callback:
            self.on_message_callback(client, userdata, msg)
    
    def _on_disconnect(self, client, userdata, rc):
        """MQTT 브로커 연결 해제 콜백"""
        self.logger.info("MQTT 브로커 연결 해제")
        
        # 외부 콜백 호출
        if self.on_disconnect_callback:
            self.on_disconnect_callback(client, userdata, rc)
    
    def connect(self, max_retries: int = 3) -> bool:
        """MQTT 브로커에 연결"""
        try:
            # MQTT 클라이언트 생성 (paho-mqtt 버전 호환성)
            try:
                # paho-mqtt 2.0+ 버전
                self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
            except AttributeError:
                # paho-mqtt 1.x 버전 (라즈베리파이 기본)
                self.client = mqtt.Client()
            
            # 콜백 설정
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect
            
            # 인증 설정
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)
            
            # 연결 시도 (재시도 로직)
            for attempt in range(max_retries):
                try:
                    self.logger.info(f"MQTT 브로커 연결 시도 {attempt + 1}/{max_retries}: {self.broker_host}:{self.broker_port}")
                    self.client.connect(self.broker_host, self.broker_port, 60)
                    return True
                except (OSError, socket.error) as e:
                    if attempt < max_retries - 1:
                        self.logger.warning(f"연결 실패 (시도 {attempt + 1}): {e}, 2초 후 재시도...")
                        time.sleep(2)
                    else:
                        self.logger.error(f"모든 연결 시도 실패: {e}")
                        raise
            
            return False
            
        except Exception as e:
            self.logger.error(f"MQTT 클라이언트 초기화 오류: {e}")
            return False
    
    def start_loop(self):
        """MQTT 메시지 루프 시작 (블로킹)"""
        if self.client:
            self.client.loop_forever()
        else:
            raise RuntimeError("MQTT 클라이언트가 초기화되지 않았습니다. connect()를 먼저 호출하세요.")
    
    def stop(self):
        """MQTT 클라이언트 중지"""
        if self.client:
            self.client.disconnect()
            self.client = None
    
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self.client and self.client.is_connected()