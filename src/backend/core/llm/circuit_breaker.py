import logging
from enum import Enum
from datetime import datetime, timedelta
from typing import Dict

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """单个模型的熔断器"""

    def __init__(
        self,
        provider_name: str,
        failure_threshold: int = 3,
        cooldown_seconds: int = 300
    ):
        self.provider_name = provider_name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.opened_at: datetime | None = None

    def allow_request(self) -> bool:
        """判断是否允许向该模型发送请求"""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if self.opened_at and datetime.now() - self.opened_at > timedelta(seconds=self.cooldown_seconds):
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker for {self.provider_name} transitioning to HALF_OPEN")
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return True

        return False

    def record_success(self):
        """记录一次成功调用"""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info(f"Circuit breaker for {self.provider_name} closed after successful probe")

    def record_failure(self):
        """记录一次失败调用"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.opened_at = datetime.now()
            logger.warning(f"Circuit breaker for {self.provider_name} reopened after failed probe")
            return

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = datetime.now()
            logger.warning(f"Circuit breaker for {self.provider_name} opened after {self.failure_count} failures")

    def get_status(self) -> Dict:
        """返回当前状态 (用于日志和监控)"""
        return {
            "provider": self.provider_name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure": str(self.last_failure_time) if self.last_failure_time else None,
            "opened_at": str(self.opened_at) if self.opened_at else None,
        }