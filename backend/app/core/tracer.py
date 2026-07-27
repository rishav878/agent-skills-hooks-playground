import uuid
from dataclasses import dataclass


@dataclass
class Span:
    span_id: str
    parent_span_id: str | None = None
    operation: str = ""


class EventTracer:
    def __init__(self, run_id: str | None = None, trace_id: str | None = None) -> None:
        self._run_id = run_id or str(uuid.uuid4())
        self._trace_id = trace_id or str(uuid.uuid4())
        self._span_stack: list[Span] = []

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def trace_id(self) -> str:
        return self._trace_id

    def start_span(self, operation: str) -> Span:
        parent = self._span_stack[-1] if self._span_stack else None
        span = Span(
            span_id=str(uuid.uuid4()),
            parent_span_id=parent.span_id if parent else None,
            operation=operation,
        )
        self._span_stack.append(span)
        return span

    def end_span(self) -> Span | None:
        if self._span_stack:
            return self._span_stack.pop()
        return None

    @property
    def current_span(self) -> Span | None:
        return self._span_stack[-1] if self._span_stack else None

    def new_child(self, run_id: str | None = None) -> "EventTracer":
        return EventTracer(
            run_id=run_id or self._run_id,
            trace_id=self._trace_id,
        )
