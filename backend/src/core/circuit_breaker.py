"""
Circuit Breaker pattern for external service resilience (T066).

Implements circuit breaker pattern per FR-017 graceful degradation requirements.
Prevents cascading failures when external services (Fabric IQ, Foundry IQ) become unresponsive.

Circuit States:
- CLOSED: Normal operation, requests pass through
- OPEN: Service failing, requests fail fast without calling service
- HALF_OPEN: Testing if service recovered, limited requests allowed

Constitutional Compliance:
- Supports graceful degradation (Principle IX)
- Enables observability with state transitions
- No hardcoded thresholds (configurable)
"""

import logging
import time
from enum import Enum
from typing import Any, Callable

from ..core.observability import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and request is rejected."""
    pass


class CircuitBreaker:
    """
    Circuit breaker for external service calls.

    Usage:
        breaker = CircuitBreaker(name="Fabric IQ", failure_threshold=5, timeout=60)
        
        async with breaker:
            result = await external_service_call()
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        half_open_max_calls: int = 1
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Service name for logging
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before trying again (OPEN → HALF_OPEN)
            half_open_max_calls: Max calls allowed in HALF_OPEN state
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0

        logger.info(
            f"CircuitBreaker '{name}' initialized: "
            f"threshold={failure_threshold}, timeout={timeout}s"
        )

    @property
    def state(self) -> CircuitState:
        """Current circuit breaker state."""
        return self._state

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self._last_failure_time is None:
            return False
        
        elapsed = time.time() - self._last_failure_time
        return elapsed >= self.timeout

    def _open_circuit(self):
        """Transition to OPEN state."""
        self._state = CircuitState.OPEN
        self._last_failure_time = time.time()
        logger.warning(
            f"CircuitBreaker '{self.name}' OPENED: "
            f"{self._failure_count} failures exceeded threshold {self.failure_threshold}"
        )

    def _close_circuit(self):
        """Transition to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0
        logger.info(f"CircuitBreaker '{self.name}' CLOSED: service recovered")

    def _half_open_circuit(self):
        """Transition to HALF_OPEN state."""
        self._state = CircuitState.HALF_OPEN
        self._half_open_calls = 0
        logger.info(
            f"CircuitBreaker '{self.name}' HALF_OPEN: testing service recovery"
        )

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result if successful

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception from func if call fails
        """
        with tracer.start_as_current_span("circuit_breaker.call") as span:
            span.set_attribute("circuit_name", self.name)
            span.set_attribute("circuit_state", self._state.value)

            # Check if we should attempt reset from OPEN → HALF_OPEN
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._half_open_circuit()
                else:
                    span.set_attribute("circuit_action", "reject")
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Service unavailable (failed {self._failure_count} times)."
                    )

            # Check HALF_OPEN call limit
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    span.set_attribute("circuit_action", "reject_half_open")
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is HALF_OPEN. "
                        "Max test calls exceeded."
                    )
                self._half_open_calls += 1

            # Attempt call
            try:
                result = await func(*args, **kwargs)
                
                # Success: Close circuit if we were testing recovery
                if self._state == CircuitState.HALF_OPEN:
                    self._close_circuit()
                    span.set_attribute("circuit_action", "closed")
                elif self._state == CircuitState.CLOSED:
                    # Reset failure count on success
                    self._failure_count = 0
                
                span.set_attribute("call_success", True)
                return result

            except Exception as e:
                # Failure: Increment count and possibly open circuit
                self._failure_count += 1
                span.set_attribute("call_success", False)
                span.set_attribute("failure_count", self._failure_count)

                if self._state == CircuitState.HALF_OPEN:
                    # Failed during recovery test → reopen circuit
                    self._open_circuit()
                    span.set_attribute("circuit_action", "reopened")
                elif self._failure_count >= self.failure_threshold:
                    # Exceeded threshold → open circuit
                    self._open_circuit()
                    span.set_attribute("circuit_action", "opened")

                logger.error(
                    f"CircuitBreaker '{self.name}' call failed: {e} "
                    f"(failures: {self._failure_count}/{self.failure_threshold})"
                )
                raise

    async def __aenter__(self):
        """Context manager entry (for async with)."""
        # Check state before allowing entry
        if self._state == CircuitState.OPEN and not self._should_attempt_reset():
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN"
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_type is None:
            # Success
            if self._state == CircuitState.HALF_OPEN:
                self._close_circuit()
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0
        else:
            # Failure
            self._failure_count += 1
            if self._state == CircuitState.HALF_OPEN:
                self._open_circuit()
            elif self._failure_count >= self.failure_threshold:
                self._open_circuit()
        
        return False  # Don't suppress exceptions
