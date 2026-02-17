"""
OPS Query SSE Handler

Provides Server-Sent Events for streaming OPS query execution progress
with ChatGPT-style status updates.

Event Types:
- progress: Stage progress updates (stage, message, elapsed_ms)
- plan: Plan generated
- tool_call: Tool execution start/complete
- block: Individual answer block streaming
- complete: Final complete event with full result
- error: Error occurred
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Literal


class OpsProgressStage(str, Enum):
    """OPS query execution stages for progress tracking."""
    
    INIT = "init"
    RESOLVING = "resolving"
    PLANNING = "planning"
    VALIDATING = "validating"
    EXECUTING = "executing"
    COMPOSING = "composing"
    PRESENTING = "presenting"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class ToolCallProgress:
    """Progress information for a tool call."""
    tool_type: str
    tool_name: str
    status: Literal["started", "completed", "error"]
    elapsed_ms: float = 0.0
    message: str = ""
    result_summary: str | None = None


@dataclass
class OpsProgressEvent:
    """Progress event data structure."""
    stage: OpsProgressStage
    message: str
    elapsed_ms: float
    details: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[ToolCallProgress] | None = None


class OpsSSEHandler:
    """
    Handler for streaming OPS query execution progress via Server-Sent Events.
    
    Provides real-time status updates similar to ChatGPT's progress indicators:
    - Shows current stage (analyzing, planning, executing tools, composing)
    - Reports tool execution progress
    - Streams answer blocks as they're generated
    """
    
    # Stage display messages (Korean)
    STAGE_MESSAGES: dict[OpsProgressStage, str] = {
        OpsProgressStage.INIT: "초기화 중...",
        OpsProgressStage.RESOLVING: "질의 분석 중...",
        OpsProgressStage.PLANNING: "실행 계획 수립 중...",
        OpsProgressStage.VALIDATING: "계획 검증 중...",
        OpsProgressStage.EXECUTING: "도구 실행 중...",
        OpsProgressStage.COMPOSING: "결과 분석 중...",
        OpsProgressStage.PRESENTING: "응답 생성 중...",
        OpsProgressStage.COMPLETE: "완료",
        OpsProgressStage.ERROR: "오류 발생",
    }
    
    # Tool type display names (Korean)
    TOOL_DISPLAY_NAMES: dict[str, str] = {
        "ci_lookup": "구성 정보 조회",
        "ci_aggregate": "구성 정보 집계",
        "ci_graph": "관계 분석",
        "metric": "메트릭 데이터 수집",
        "event_log": "이력 검색",
        "document_search": "문서 검색",
        "http_api": "API 호출",
        "database_query": "데이터베이스 조회",
        "graph_query": "그래프 조회",
    }
    
    def __init__(self):
        self._start_time: float = 0
        self._current_stage: OpsProgressStage = OpsProgressStage.INIT
        self._completed_stages: list[OpsProgressStage] = []
        self._tool_calls: list[ToolCallProgress] = []
    
    def _elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds since start."""
        return round((time.perf_counter() - self._start_time) * 1000, 1)
    
    def _sse_event(self, event_type: str, data: dict[str, Any]) -> str:
        """
        Format data as SSE event.
        
        Format:
        event: {event_type}
        data: {json_string}
        """
        return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    
    def _progress_event(
        self,
        stage: OpsProgressStage,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> str:
        """Create a progress event."""
        self._current_stage = stage
        if message is None:
            message = self.STAGE_MESSAGES.get(stage, "처리 중...")
        
        return self._sse_event("progress", {
            "stage": stage.value,
            "message": message,
            "elapsed_ms": self._elapsed_ms(),
            "details": details or {},
            "completed_stages": [s.value for s in self._completed_stages],
        })
    
    def _tool_call_event(self, tool_progress: ToolCallProgress) -> str:
        """Create a tool call progress event."""
        return self._sse_event("tool_call", {
            "tool_type": tool_progress.tool_type,
            "tool_name": tool_progress.tool_name,
            "display_name": self.TOOL_DISPLAY_NAMES.get(
                tool_progress.tool_type, tool_progress.tool_name
            ),
            "status": tool_progress.status,
            "elapsed_ms": tool_progress.elapsed_ms,
            "message": tool_progress.message,
            "result_summary": tool_progress.result_summary,
        })
    
    def _block_event(self, block: dict[str, Any], index: int, total: int) -> str:
        """Create a block streaming event."""
        return self._sse_event("block", {
            "block": block,
            "index": index,
            "total": total,
            "elapsed_ms": self._elapsed_ms(),
        })
    
    def _complete_event(self, result: dict[str, Any]) -> str:
        """Create a complete event with final result."""
        self._completed_stages.append(OpsProgressStage.COMPLETE)
        return self._sse_event("complete", {
            **result,
            "timing": {
                "total_ms": self._elapsed_ms(),
            },
            "completed_stages": [s.value for s in self._completed_stages],
        })
    
    def _error_event(self, error_message: str, stage: str = "unknown") -> str:
        """Create an error event."""
        return self._sse_event("error", {
            "message": error_message,
            "stage": stage,
            "elapsed_ms": self._elapsed_ms(),
        })
    
    async def stream_ops_query(
        self,
        *,
        question: str,
        tenant_id: str,
        user_id: str,
        runner_func: Callable[..., dict[str, Any]],
        **runner_kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """
        Stream OPS query execution with progress updates.
        
        Args:
            question: User's question
            tenant_id: Tenant ID
            user_id: User ID
            runner_func: Async or sync function that executes the query
            **runner_kwargs: Additional arguments for runner_func
            
        Yields:
            SSE-formatted event strings
        """
        self._start_time = time.perf_counter()
        self._tool_calls = []
        self._completed_stages = []
        
        try:
            # Stage 1: Init
            yield self._progress_event(
                OpsProgressStage.INIT,
                "질의 처리 시작...",
                {"question_preview": question[:100] + ("..." if len(question) > 100 else "")}
            )
            
            # Stage 2: Resolving
            yield self._progress_event(
                OpsProgressStage.RESOLVING,
                "질의 분석 중...",
            )
            self._completed_stages.append(OpsProgressStage.INIT)
            
            # Stage 3: Planning (will be done inside runner)
            yield self._progress_event(
                OpsProgressStage.PLANNING,
                "실행 계획 수립 중...",
            )
            self._completed_stages.append(OpsProgressStage.RESOLVING)
            
            # Execute the runner with a callback for progress updates
            async def on_stage_change(stage: str, details: dict[str, Any] | None = None):
                """Callback for stage changes during execution."""
                nonlocal self
                try:
                    ops_stage = OpsProgressStage(stage)
                    yield self._progress_event(ops_stage, details=details)
                except ValueError:
                    pass  # Unknown stage, ignore
            
            async def on_tool_call(
                tool_type: str,
                tool_name: str,
                status: str,
                result_summary: str | None = None,
            ):
                """Callback for tool call progress."""
                tool_progress = ToolCallProgress(
                    tool_type=tool_type,
                    tool_name=tool_name,
                    status=status,
                    elapsed_ms=self._elapsed_ms(),
                    result_summary=result_summary,
                )
                self._tool_calls.append(tool_progress)
                yield self._tool_call_event(tool_progress)
            
            # Stage 4: Executing
            yield self._progress_event(
                OpsProgressStage.EXECUTING,
                "데이터 조회 및 분석 중...",
            )
            self._completed_stages.append(OpsProgressStage.PLANNING)
            
            # Run the actual query
            import asyncio
            import inspect
            
            if inspect.iscoroutinefunction(runner_func):
                result = await runner_func(**runner_kwargs)
            else:
                # Run sync function in thread pool
                result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: runner_func(**runner_kwargs)
                )
            
            self._completed_stages.append(OpsProgressStage.EXECUTING)
            
            # Stage 5: Composing - stream blocks if available
            yield self._progress_event(
                OpsProgressStage.COMPOSING,
                "결과 분석 및 종합 중...",
            )
            
            blocks = result.get("blocks", [])
            if blocks:
                for i, block in enumerate(blocks):
                    yield self._block_event(block, i, len(blocks))
            
            self._completed_stages.append(OpsProgressStage.COMPOSING)
            
            # Stage 6: Presenting
            yield self._progress_event(
                OpsProgressStage.PRESENTING,
                "응답 생성 완료",
            )
            self._completed_stages.append(OpsProgressStage.PRESENTING)
            
            # Final complete event
            yield self._complete_event(result)
            
        except Exception as e:
            yield self._error_event(str(e), self._current_stage.value)


# Global handler instance
ops_sse_handler = OpsSSEHandler()
