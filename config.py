"""
설정 관리 모듈
환경 변수 및 기본 설정 관리
"""
import os
import logging
from dataclasses import dataclass
from typing import Optional


@dataclass
class MQTTConfig:
    """MQTT 관련 설정"""
    broker_host: str = "localhost"
    broker_port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    connection_retries: int = 3
    connection_timeout: int = 60


@dataclass
class DatabaseConfig:
    """데이터베이스 관련 설정"""
    enable_sqlite: bool = True
    db_path: str = "lora_gateway.db"


@dataclass
class LoggingConfig:
    """로깅 관련 설정"""
    log_level: str = "INFO"
    log_file: str = "lora_gateway.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    syslog_host: Optional[str] = None
    syslog_port: int = 514


@dataclass
class AppConfig:
    """애플리케이션 전체 설정"""
    mqtt: MQTTConfig
    database: DatabaseConfig
    logging: LoggingConfig
    stats_interval: int = 300  # 5분마다 통계 출력


def load_config_from_env() -> AppConfig:
    """환경 변수에서 설정 로드"""
    
    # MQTT 설정
    mqtt_config = MQTTConfig(
        broker_host=os.getenv('MQTT_BROKER_HOST', 'localhost'),
        broker_port=int(os.getenv('MQTT_BROKER_PORT', '1883')),
        username=os.getenv('MQTT_USERNAME'),
        password=os.getenv('MQTT_PASSWORD'),
        connection_retries=int(os.getenv('MQTT_CONNECTION_RETRIES', '3')),
        connection_timeout=int(os.getenv('MQTT_CONNECTION_TIMEOUT', '60'))
    )
    
    # 데이터베이스 설정
    database_config = DatabaseConfig(
        enable_sqlite=os.getenv('ENABLE_SQLITE', 'true').lower() == 'true',
        db_path=os.getenv('DATABASE_PATH', 'lora_gateway.db')
    )
    
    # 로깅 설정
    logging_config = LoggingConfig(
        log_level=os.getenv('LOG_LEVEL', 'INFO').upper(),
        log_file=os.getenv('LOG_FILE', 'lora_gateway.log'),
        max_file_size=int(os.getenv('LOG_MAX_SIZE', str(10 * 1024 * 1024))),
        backup_count=int(os.getenv('LOG_BACKUP_COUNT', '5')),
        syslog_host=os.getenv('SYSLOG_HOST'),
        syslog_port=int(os.getenv('SYSLOG_PORT', '514'))
    )
    
    # 애플리케이션 설정
    app_config = AppConfig(
        mqtt=mqtt_config,
        database=database_config,
        logging=logging_config,
        stats_interval=int(os.getenv('STATS_INTERVAL', '300'))
    )
    
    return app_config


def setup_logging(config: LoggingConfig):
    """로깅 설정 초기화"""
    import socket
    from logging.handlers import RotatingFileHandler, SysLogHandler
    
    log_handlers = []
    
    # 파일 로깅 (로테이션 지원)
    file_handler = RotatingFileHandler(
        config.log_file,
        maxBytes=config.max_file_size,
        backupCount=config.backup_count,
        encoding='utf-8'
    )
    log_handlers.append(file_handler)
    
    # 콘솔 로깅
    console_handler = logging.StreamHandler()
    log_handlers.append(console_handler)
    
    # 원격 syslog 지원 (라즈베리파이에서 PC로 로그 전송)
    if config.syslog_host:
        try:
            syslog_handler = SysLogHandler(
                address=(config.syslog_host, config.syslog_port)
            )
            syslog_handler.setFormatter(logging.Formatter(
                f'{socket.gethostname()} lora-gateway: %(levelname)s - %(message)s'
            ))
            log_handlers.append(syslog_handler)
        except Exception as e:
            print(f"Syslog 설정 실패: {e}")
    
    # 로깅 기본 설정
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        handlers=log_handlers
    )
    
    # UTF-8 인코딩 설정 (Windows)
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')