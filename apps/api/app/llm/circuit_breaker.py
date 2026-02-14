"""Circuit breaker pattern for LLM service resilience"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """States of the circuit breaker"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Service failure detected, fast-fail requests
    HALF_OPEN = "half_open"  # Recovery mode, testing if service is healthy


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior"""

    failure_threshold: int = 5  # Consecutive failures before open
    recovery_timeout: float = 60.0  # Seconds before attempting recovery
    success_threshold: int = 2  # Consecutive successes in HALF_OPEN to close
    expected_exception: type = Exception


@dataclass
class CircuitBreaker:
    """Circuit breaker implementation for service fault tolerance"""

    config: CircuitBreakerConfig
    name: str = "LLM"
    _failure_count: int = field(default=0, init=False, repr=False)
    _success_count: int = field(default=0, init=False, repr=False)
    _last_failure_time: float = field(default=0.0, init=False, repr=False)
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False, repr=False)

    def _log_state_change(self, old_state: CircuitState, new_state: CircuitState) -> None:
        """Log circuit breaker state transitions"""
        if old_state != new_state:
            logger.warning(
                f"Circuit breaker '{self.name}' state transition: {old_state} → {new_state}"
            )

    def is_open(self) -> bool:
        """Check if circuit should be open (fast-fail mode)"""
        if self._state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            elapsed = time.time() - self._last_failure_time
            if elapsed > self.config.recovery_timeout:
                old_state = self._state
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                self._log_state_change(old_state, self._state)
                logger.info(
                    f"Circuit breaker '{self.name}' transitioning to HALF_OPEN "
                    f"(recovery timeout passed after {elapsed:.1f}s)"
                )
                return False
            return True
        return False

    def record_success(self) -> None:
        """Record successful operation"""
        if self._state == CircuitState.CLOSED:
            # In CLOSED state, just reset failure count
            self._failure_count = 0
        elif self._state == CircuitState.HALF_OPEN:
            # In HALF_OPEN state, increment success count
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                old_state = self._state
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                self._log_state_change(old_state, self._state)
                logger.info(
                    f"Circuit breaker '{self.name}' closed after successful recovery "
                    f"({self._success_count} consecutive successes)"
                )

    def record_failure(self) -> None:
        """Record failed operation"""
        self._last_failure_time = time.time()

        if self._state == CircuitState.CLOSED:
            # In CLOSED state, increment failure count
            self._failure_count += 1
            if self._failure_count >= self.config.failure_threshold:
                old_state = self._state
                self._state = CircuitState.OPEN
                self._log_state_change(old_state, self._state)
                logger.warning(
                    f"Circuit breaker '{self.name}' opened after "
                    f"{self._failure_count} consecutive failures"
                )
        elif self._state == CircuitState.HALF_OPEN:
            # In HALF_OPEN state, any failure returns to OPEN
            old_state = self._state
            self._state = CircuitState.OPEN
            self._failure_count = 1
            self._success_count = 0
            self._log_state_change(old_state, self._state)
            logger.warning(
                f"Circuit breaker '{self.name}' reopened during recovery attempt"
            )

    @property
    def state(self) -> CircuitState:
        """Get current state (with auto-refresh for recovery timeout)"""
        self.is_open()  # Updates state if recovery timeout passed
        return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count"""
        return self._failure_count

    @property
    def success_count(self) -> int:
        """Get current success count (in HALF_OPEN state)"""
        return self._success_count

    def get_stats(self) -> dict:
        """Get circuit breaker statistics for monitoring"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_time": self._last_failure_time,
            "failure_threshold": self.config.failure_threshold,
            "recovery_timeout": self.config.recovery_timeout,
            "success_threshold": self.config.success_threshold,
        }

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state"""
        old_state = self._state
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._log_state_change(old_state, self._state)
        logger.info(f"Circuit breaker '{self.name}' manually reset")

    def __str__(self) -> str:
        return (
            f"CircuitBreaker(name={self.name}, state={self.state.value}, "
            f"failures={self._failure_count}, successes={self._success_count})"
        )

    def __repr__(self) -> str:
        return self.__str__()


class CircuitBreakerManager:
    """Manager for multiple circuit breakers"""

    _breakers: dict[str, CircuitBreaker] = {}

    @classmethod
    def get_or_create(
        cls,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreaker:
        """Get or create a circuit breaker by name"""
        if name not in cls._breakers:
            if config is None:
                config = CircuitBreakerConfig()
            cls._breakers[name] = CircuitBreaker(config, name=name)
        return cls._breakers[name]

    @classmethod
    def get(cls, name: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by name, return None if not found"""
        return cls._breakers.get(name)

    @classmethod
    def get_all_stats(cls) -> dict[str, dict]:
        """Get stats for all circuit breakers"""
        return {name: breaker.get_stats() for name, breaker in cls._breakers.items()}

    @classmethod
    def reset_all(cls) -> None:
        """Reset all circuit breakers"""
        for breaker in cls._breakers.values():
            breaker.reset()

    @classmethod
    def clear(cls) -> None:
        """Clear all circuit breakers"""
        cls._breakers.clear()
