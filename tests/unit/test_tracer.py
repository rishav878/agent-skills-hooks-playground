from app.core.tracer import EventTracer


class TestEventTracer:
    def test_run_id_generated(self) -> None:
        t = EventTracer()
        assert t.run_id is not None
        assert len(t.run_id) > 0

    def test_trace_id_generated(self) -> None:
        t = EventTracer()
        assert t.trace_id is not None
        assert len(t.trace_id) > 0

    def test_run_id_provided(self) -> None:
        t = EventTracer(run_id="my-run")
        assert t.run_id == "my-run"

    def test_trace_id_provided(self) -> None:
        t = EventTracer(trace_id="my-trace")
        assert t.trace_id == "my-trace"

    def test_start_span_no_parent(self) -> None:
        t = EventTracer()
        span = t.start_span("test")
        assert span.operation == "test"
        assert span.parent_span_id is None

    def test_start_span_with_parent(self) -> None:
        t = EventTracer()
        parent = t.start_span("parent")
        child = t.start_span("child")
        assert child.parent_span_id == parent.span_id
        assert child.operation == "child"

    def test_end_span_pops(self) -> None:
        t = EventTracer()
        t.start_span("first")
        t.start_span("second")
        ended = t.end_span()
        assert ended is not None
        assert ended.operation == "second"
        assert t.current_span is not None
        assert t.current_span.operation == "first"

    def test_end_span_empty_stack(self) -> None:
        t = EventTracer()
        assert t.end_span() is None

    def test_current_span_none_when_empty(self) -> None:
        t = EventTracer()
        assert t.current_span is None

    def test_current_span_returns_top(self) -> None:
        t = EventTracer()
        t.start_span("top")
        assert t.current_span is not None
        assert t.current_span.operation == "top"

    def test_new_child_preserves_trace_id(self) -> None:
        t = EventTracer(run_id="parent-run", trace_id="parent-trace")
        child = t.new_child()
        assert child.trace_id == "parent-trace"
        assert child.run_id == "parent-run"

    def test_new_child_with_different_run_id(self) -> None:
        t = EventTracer(run_id="parent-run", trace_id="parent-trace")
        child = t.new_child(run_id="child-run")
        assert child.trace_id == "parent-trace"
        assert child.run_id == "child-run"

    def test_multiple_spans_nesting(self) -> None:
        t = EventTracer()
        t.start_span("a")
        t.start_span("b")
        t.start_span("c")
        assert t.current_span is not None and t.current_span.operation == "c"
        t.end_span()
        assert t.current_span is not None and t.current_span.operation == "b"
        t.end_span()
        assert t.current_span is not None and t.current_span.operation == "a"
        t.end_span()
        assert t.current_span is None
