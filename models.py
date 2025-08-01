"""
LoRa Gateway Logger 데이터 모델
업링크 메시지와 관련된 데이터 클래스 정의
"""
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional


@dataclass
class UplinkMessage:
    """LoRa 업링크 메시지 데이터 클래스"""
    
    # 필수 필드
    timestamp: datetime
    application_id: str
    device_id: str
    
    # 페이로드 정보
    payload_base64: Optional[str] = None
    payload_hex: Optional[str] = None
    payload_text: Optional[str] = None
    payload_size: Optional[int] = None
    
    # 디바이스 및 네트워크 정보
    dev_eui: Optional[str] = None
    frame_count: Optional[int] = None
    f_port: Optional[int] = None
    frequency: Optional[int] = None
    data_rate: Optional[int] = None
    
    # 신호 품질
    rssi: Optional[float] = None
    snr: Optional[float] = None
    
    # 위치 정보
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # 메타데이터
    hostname: Optional[str] = None
    raw_topic: Optional[str] = None
    
    # 데이터베이스 전용 필드
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    
    def __str__(self) -> str:
        """사람이 읽기 쉬운 문자열 표현"""
        return (f"UplinkMessage(app={self.application_id}, "
                f"device={self.device_id}, "
                f"text='{self.payload_text}', "
                f"frame_count={self.frame_count})")
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환 (JSON 직렬화용)"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result
    
    @classmethod
    def from_payload_summary(cls, payload_summary: dict, 
                           application_id: str, device_id: str, 
                           raw_topic: str, hostname: str) -> 'UplinkMessage':
        """페이로드 요약 정보에서 UplinkMessage 생성"""
        
        # 디코딩된 데이터 추출
        decoded_data = payload_summary.get('decoded_data', {})
        
        # KST 타임존 설정 (UTC+9)
        kst = timezone(timedelta(hours=9))
        
        return cls(
            timestamp=datetime.now(kst),
            application_id=application_id,
            device_id=device_id,
            dev_eui=payload_summary.get('devEUI'),
            
            # 페이로드 정보
            payload_base64=payload_summary.get('data'),
            payload_hex=decoded_data.get('hex'),
            payload_text=decoded_data.get('text'),
            payload_size=payload_summary.get('data_size'),
            
            # 네트워크 정보
            frame_count=payload_summary.get('fCnt'),
            f_port=payload_summary.get('fPort'),
            frequency=payload_summary.get('frequency'),
            data_rate=payload_summary.get('dataRate'),
            
            # 신호 품질
            rssi=payload_summary.get('rssi'),
            snr=payload_summary.get('snr'),
            
            # 위치 정보
            latitude=payload_summary.get('latitude'),
            longitude=payload_summary.get('longitude'),
            
            # 메타데이터
            hostname=hostname,
            raw_topic=raw_topic
        )


@dataclass
class JoinEvent:
    """LoRa 디바이스 JOIN 이벤트 데이터 클래스"""
    
    # 필수 필드
    timestamp: datetime
    application_id: str
    device_id: str
    dev_eui: str
    
    # JOIN 관련 정보
    join_eui: Optional[str] = None  # AppEUI/JoinEUI
    dev_addr: Optional[str] = None  # 할당된 디바이스 주소
    
    # 네트워크 정보
    frequency: Optional[int] = None
    data_rate: Optional[int] = None
    
    # 신호 품질
    rssi: Optional[float] = None
    snr: Optional[float] = None
    
    # 위치 정보
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # 메타데이터
    hostname: Optional[str] = None
    raw_topic: Optional[str] = None
    
    # 데이터베이스 전용 필드
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    
    def __str__(self) -> str:
        """사람이 읽기 쉬운 문자열 표현"""
        return (f"JoinEvent(app={self.application_id}, "
                f"device={self.device_id}, "
                f"dev_eui={self.dev_eui}, "
                f"dev_addr={self.dev_addr})")
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환 (JSON 직렬화용)"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result
    
    @classmethod
    def from_payload_summary(cls, payload_summary: dict, 
                           application_id: str, device_id: str, 
                           raw_topic: str, hostname: str) -> 'JoinEvent':
        """페이로드 요약 정보에서 JoinEvent 생성"""
        
        # KST 타임존 설정 (UTC+9)
        kst = timezone(timedelta(hours=9))
        
        return cls(
            timestamp=datetime.now(kst),
            application_id=application_id,
            device_id=device_id,
            dev_eui=payload_summary.get('devEUI'),
            join_eui=payload_summary.get('joinEUI'),
            dev_addr=payload_summary.get('devAddr'),
            
            # 네트워크 정보
            frequency=payload_summary.get('frequency'),
            data_rate=payload_summary.get('dataRate'),
            
            # 신호 품질
            rssi=payload_summary.get('rssi'),
            snr=payload_summary.get('snr'),
            
            # 위치 정보
            latitude=payload_summary.get('latitude'),
            longitude=payload_summary.get('longitude'),
            
            # 메타데이터
            hostname=hostname,
            raw_topic=raw_topic
        )