"""
LoRa 메시지 파싱 모듈
MQTT 페이로드를 파싱하고 데이터 구조화
"""
import json
import base64
import logging
from typing import Dict, Optional, Tuple


class LoRaMessageParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse_topic(self, topic: str) -> Optional[Tuple[str, str, str]]:
        """토픽을 파싱하여 application_id, device_id, event_type 추출"""
        try:
            topic_parts = topic.split('/')
            if len(topic_parts) < 6:
                self.logger.warning(f"잘못된 토픽 형식: {topic}")
                return None
                
            application_id = topic_parts[1]
            device_id = topic_parts[3]
            event_type = topic_parts[5]  # 'up' 또는 'join'
            
            return application_id, device_id, event_type
            
        except Exception as e:
            self.logger.error(f"토픽 파싱 오류: {e}")
            return None
    
    def parse_payload(self, payload_bytes: bytes) -> Optional[Dict]:
        """MQTT 페이로드를 JSON으로 파싱"""
        try:
            return json.loads(payload_bytes.decode('utf-8'))
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 파싱 오류: {e} - Raw payload: {payload_bytes}")
            return None
        except Exception as e:
            self.logger.error(f"페이로드 파싱 오류: {e}")
            return None
    
    def extract_uplink_summary(self, payload: Dict) -> Dict:
        """업링크 페이로드에서 주요 정보 추출"""
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
            self.logger.debug(f"업링크 정보 추출 오류: {e}")
            
        return summary
    
    def extract_join_summary(self, payload: Dict) -> Dict:
        """JOIN 이벤트에서 주요 정보 추출"""
        summary = {}
        
        try:
            # 기본 디바이스 정보
            summary['devEUI'] = payload.get('devEUI')
            summary['joinEUI'] = payload.get('joinEUI') or payload.get('appEUI')  # joinEUI 또는 appEUI
            summary['devAddr'] = payload.get('devAddr')
            
            # RSSI와 SNR 추출 (첫 번째 게이트웨이 기준)
            if 'rxInfo' in payload and len(payload['rxInfo']) > 0:
                rx_info = payload['rxInfo'][0]
                summary['rssi'] = rx_info.get('rssi')
                summary['snr'] = rx_info.get('loRaSNR')
                
                # 위치 정보도 추출
                if 'location' in rx_info:
                    summary['latitude'] = rx_info['location'].get('latitude')
                    summary['longitude'] = rx_info['location'].get('longitude')
            
            # 전송 정보 추출
            if 'txInfo' in payload:
                tx_info = payload['txInfo']
                summary['frequency'] = tx_info.get('frequency')
                summary['dataRate'] = tx_info.get('dr')
                
        except Exception as e:
            self.logger.debug(f"JOIN 이벤트 정보 추출 오류: {e}")
            
        return summary
    
    def _decode_payload_data(self, data: str) -> Dict:
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