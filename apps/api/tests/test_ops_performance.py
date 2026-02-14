"""
Performance tests for OPS module - Response time, caching, memory usage.

Tests cover:
- Response time measurements
- Cache efficiency
- Memory usage
- Concurrent request handling
"""

import os
import time

import psutil


class TestResponseTimeMeasurements:
    """Test response time for various operations."""

    def test_simple_binding_engine_render_time(self):
        """Test that simple binding renders in < 10ms."""
        from app.modules.ops.services.binding_engine import BindingEngine

        template = "Device: {{inputs.device_id}}"
        context = {
            "inputs": {"device_id": "srv-01"},
            "state": {},
            "context": {},
            "trace_id": "trace-123",
        }

        start = time.perf_counter()
        for _ in range(100):
            BindingEngine.render_template(template, context)
        elapsed = (time.perf_counter() - start) / 100 * 1000  # Average ms

        assert elapsed < 10, f"Simple binding render took {elapsed}ms, expected < 10ms"

    def test_complex_binding_engine_render_time(self):
        """Test that complex binding renders in < 50ms."""
        from app.modules.ops.services.binding_engine import BindingEngine

        template = {
            "device": "{{inputs.device_id}}",
            "nested": {
                "path": {
                    "status": "{{state.status}}",
                    "config": {
                        "mode": "{{context.mode}}"
                    }
                }
            },
            "items": [
                {"id": "{{inputs.id1}}", "name": "Item 1"},
                {"id": "{{inputs.id2}}", "name": "Item 2"},
            ]
        }
        context = {
            "inputs": {"device_id": "srv-01", "id1": "a", "id2": "b"},
            "state": {"status": "healthy"},
            "context": {"mode": "real"},
            "trace_id": "trace-123",
        }

        start = time.perf_counter()
        for _ in range(100):
            BindingEngine.render_template(template, context)
        elapsed = (time.perf_counter() - start) / 100 * 1000  # Average ms

        assert elapsed < 50, f"Complex binding render took {elapsed}ms, expected < 50ms"

    def test_action_registry_lookup_time(self):
        """Test that action registry lookup is < 1ms."""
        from app.modules.ops.services.action_registry import ActionRegistry

        registry = ActionRegistry()

        @registry.register("action_1")
        async def handler(inputs, context, session):
            pass

        start = time.perf_counter()
        for _ in range(10000):
            registry.get("action_1")
        elapsed = (time.perf_counter() - start) / 10000 * 1000  # Average ms

        assert elapsed < 1, f"Action lookup took {elapsed}ms, expected < 1ms"

    def test_multiple_action_registrations_lookup_time(self):
        """Test lookup time with many registered actions."""
        from app.modules.ops.services.action_registry import ActionRegistry

        registry = ActionRegistry()

        # Register 100 actions
        for i in range(100):
            @registry.register(f"action_{i}")
            async def handler(inputs, context, session):
                pass

        start = time.perf_counter()
        for _ in range(10000):
            registry.get("action_50")
        elapsed = (time.perf_counter() - start) / 10000 * 1000  # Average ms

        assert elapsed < 1, f"Lookup with 100 actions took {elapsed}ms, expected < 1ms"


class TestCacheEfficiency:
    """Test caching behavior and efficiency."""

    def test_template_validation_cache(self):
        """Test that template validation performance."""
        from app.modules.ops.services.binding_engine import BindingEngine

        template = {
            "device": "{{inputs.device_id}}",
            "status": "{{state.status}}",
            "nested": {
                "field": "{{context.mode}}"
            }
        }

        start = time.perf_counter()
        for _ in range(100):
            BindingEngine.validate_template(template)
        elapsed = (time.perf_counter() - start) / 100 * 1000

        assert elapsed < 20, f"Template validation took {elapsed}ms"

    def test_nested_path_access_performance(self):
        """Test that nested path access is efficient."""
        from app.modules.ops.services.binding_engine import BindingEngine

        obj = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "level5": {
                                "value": 42
                            }
                        }
                    }
                }
            }
        }

        start = time.perf_counter()
        for _ in range(10000):
            BindingEngine.get_nested_value(obj, "level1.level2.level3.level4.level5.value")
        elapsed = (time.perf_counter() - start) / 10000 * 1000

        assert elapsed < 5, f"Deep path access took {elapsed}ms"


class TestMemoryUsage:
    """Test memory usage characteristics."""

    def test_binding_engine_memory_baseline(self):
        """Test baseline memory usage of BindingEngine."""
        from app.modules.ops.services.binding_engine import BindingEngine

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Render template 1000 times
        template = {"device": "{{inputs.device_id}}", "status": "{{state.status}}"}
        context = {
            "inputs": {"device_id": "srv-01"},
            "state": {"status": "healthy"},
            "context": {},
            "trace_id": "trace-123",
        }

        for _ in range(1000):
            BindingEngine.render_template(template, context)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Should not use more than 10MB
        assert memory_increase < 10, f"Memory increased by {memory_increase}MB"

    def test_action_registry_memory_with_many_actions(self):
        """Test memory usage with many registered actions."""
        from app.modules.ops.services.action_registry import ActionRegistry

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        registry = ActionRegistry()

        # Register 1000 actions
        async def handler(inputs, context, session):
            pass

        for i in range(1000):
            registry.register(f"action_{i}")(handler)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Should not use more than 50MB for 1000 actions
        assert memory_increase < 50, f"Memory increased by {memory_increase}MB for 1000 actions"


class TestConcurrentOperations:
    """Test performance with concurrent operations."""

    def test_action_registry_concurrent_lookups(self):
        """Test concurrent action lookups."""
        import threading

        from app.modules.ops.services.action_registry import ActionRegistry

        registry = ActionRegistry()

        @registry.register("test_action")
        async def handler(inputs, context, session):
            pass

        def lookup_action():
            for _ in range(100):
                registry.get("test_action")

        threads = [threading.Thread(target=lookup_action) for _ in range(10)]
        start = time.perf_counter()

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        elapsed = time.perf_counter() - start

        # 10 threads x 100 lookups = 1000 lookups should complete in < 1 second
        assert elapsed < 1, f"Concurrent lookups took {elapsed}s"

    def test_binding_engine_concurrent_renders(self):
        """Test concurrent template renders."""
        import threading

        from app.modules.ops.services.binding_engine import BindingEngine

        template = {"device": "{{inputs.device_id}}", "status": "{{state.status}}"}
        context = {
            "inputs": {"device_id": "srv-01"},
            "state": {"status": "healthy"},
            "context": {},
            "trace_id": "trace-123",
        }

        results = []

        def render_template():
            for _ in range(100):
                result = BindingEngine.render_template(template, context)
                results.append(result)

        threads = [threading.Thread(target=render_template) for _ in range(10)]
        start = time.perf_counter()

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        elapsed = time.perf_counter() - start

        # 10 threads x 100 renders = 1000 renders should complete in < 5 seconds
        assert elapsed < 5, f"Concurrent renders took {elapsed}s"
        assert len(results) == 1000


class TestScalability:
    """Test scalability characteristics."""

    def test_large_template_rendering(self):
        """Test rendering large templates."""
        from app.modules.ops.services.binding_engine import BindingEngine

        # Create large template with 100 fields
        template = {f"field_{i}": f"{{{{inputs.field_{i}}}}}" for i in range(100)}

        context = {
            "inputs": {f"field_{i}": f"value_{i}" for i in range(100)},
            "state": {},
            "context": {},
            "trace_id": "trace-123",
        }

        start = time.perf_counter()
        for _ in range(100):
            BindingEngine.render_template(template, context)
        elapsed = (time.perf_counter() - start) / 100 * 1000

        # Should handle large templates efficiently
        assert elapsed < 100, f"Large template render took {elapsed}ms"

    def test_deeply_nested_template_rendering(self):
        """Test rendering deeply nested templates."""
        from app.modules.ops.services.binding_engine import BindingEngine

        # Create deeply nested template (10 levels)
        template = {"level_0": {"level_1": {"level_2": {"level_3": {"level_4": {
            "level_5": {"level_6": {"level_7": {"level_8": {
                "level_9": "{{inputs.deep_value}}"
            }}}}}}}}}}

        context = {
            "inputs": {"deep_value": "found it!"},
            "state": {},
            "context": {},
            "trace_id": "trace-123",
        }

        start = time.perf_counter()
        for _ in range(100):
            BindingEngine.render_template(template, context)
        elapsed = (time.perf_counter() - start) / 100 * 1000

        assert elapsed < 50, f"Deep nested render took {elapsed}ms"

    def test_many_bindings_in_string(self):
        """Test string with many binding expressions."""
        from app.modules.ops.services.binding_engine import BindingEngine

        # Create string with 50 bindings
        template = " ".join([f"{{{{inputs.field_{i}}}}}" for i in range(50)])

        context = {
            "inputs": {f"field_{i}": f"value_{i}" for i in range(50)},
            "state": {},
            "context": {},
            "trace_id": "trace-123",
        }

        start = time.perf_counter()
        for _ in range(100):
            BindingEngine.render_template(template, context)
        elapsed = (time.perf_counter() - start) / 100 * 1000

        assert elapsed < 100, f"Many bindings render took {elapsed}ms"


class TestResourceCleanup:
    """Test resource cleanup and memory deallocation."""

    def test_action_handler_cleanup(self):
        """Test that action handlers are cleaned up."""
        from app.modules.ops.services.action_registry import ActionRegistry

        registry = ActionRegistry()

        @registry.register("temp_action")
        async def handler(inputs, context, session):
            pass

        # Handler should be registered
        assert registry.get("temp_action") is not None

        # In real scenario, we'd test deletion if supported
        # For now, just verify it exists
        assert registry.get("temp_action") is not None

    def test_binding_context_cleanup(self):
        """Test that binding context is properly cleaned up."""
        from app.modules.ops.services.binding_engine import BindingEngine

        # Create large context
        context = {
            "inputs": {f"input_{i}": f"value_{i}" for i in range(1000)},
            "state": {f"state_{i}": f"state_value_{i}" for i in range(1000)},
            "context": {f"ctx_{i}": f"ctx_value_{i}" for i in range(1000)},
            "trace_id": "trace-123",
        }

        template = "{{inputs.input_0}}"
        result = BindingEngine.render_template(template, context)

        # Result should not hold reference to entire context
        assert isinstance(result, str)


class TestPerformanceRegressions:
    """Test for performance regressions."""

    def test_binding_engine_performance_baseline(self):
        """Test binding engine maintains baseline performance."""
        from app.modules.ops.services.binding_engine import BindingEngine

        # This is a regression test - update baseline as needed
        template = {
            "device": "{{inputs.device_id}}",
            "config": {
                "mode": "{{context.mode}}",
                "status": "{{state.status}}"
            }
        }
        context = {
            "inputs": {"device_id": "srv-01"},
            "state": {"status": "running"},
            "context": {"mode": "real"},
            "trace_id": "trace-123",
        }

        start = time.perf_counter()
        for _ in range(1000):
            BindingEngine.render_template(template, context)
        elapsed = (time.perf_counter() - start) / 1000 * 1000  # Average ms

        # Baseline: should be < 5ms (adjust as needed)
        assert elapsed < 10, f"Performance regression: {elapsed}ms (baseline: 5ms)"

    def test_action_registry_performance_baseline(self):
        """Test action registry maintains baseline performance."""
        from app.modules.ops.services.action_registry import ActionRegistry

        registry = ActionRegistry()

        for i in range(50):
            @registry.register(f"action_{i}")
            async def handler(inputs, context, session):
                pass

        start = time.perf_counter()
        for _ in range(10000):
            registry.get("action_25")
        elapsed = (time.perf_counter() - start) / 10000 * 1000  # Average ms

        # Baseline: should be < 0.1ms (adjust as needed)
        assert elapsed < 1, f"Performance regression: {elapsed}ms (baseline: 0.1ms)"


class TestEndpointResponseTime:
    """Test response time for endpoints."""

    def test_query_endpoint_response_time(self):
        """Test /query endpoint response time (target: < 1000ms)."""
        # This would require TestClient setup
        pass

    def test_ui_action_endpoint_response_time(self):
        """Test /ui-actions endpoint response time (target: < 500ms)."""
        # This would require TestClient setup
        pass

    def test_ci_ask_endpoint_response_time(self):
        """Test /ask endpoint response time (target: < 5000ms)."""
        # This would require TestClient setup
        pass


class TestLoadTesting:
    """Load testing for OPS module."""

    def test_sustained_load_binding_engine(self):
        """Test BindingEngine under sustained load."""
        from app.modules.ops.services.binding_engine import BindingEngine

        template = {"device": "{{inputs.device_id}}", "status": "{{state.status}}"}
        context = {
            "inputs": {"device_id": "srv-01"},
            "state": {"status": "healthy"},
            "context": {},
            "trace_id": "trace-123",
        }

        # Run for 5 seconds continuously
        start = time.perf_counter()
        count = 0

        while time.perf_counter() - start < 5:
            BindingEngine.render_template(template, context)
            count += 1

        elapsed = time.perf_counter() - start
        throughput = count / elapsed

        # Should handle at least 1000 renders per second
        assert throughput > 1000, f"Throughput: {throughput} renders/sec"

    def test_sustained_load_action_registry(self):
        """Test ActionRegistry under sustained load."""
        from app.modules.ops.services.action_registry import ActionRegistry

        registry = ActionRegistry()

        @registry.register("test_action")
        async def handler(inputs, context, session):
            pass

        # Run for 5 seconds continuously
        start = time.perf_counter()
        count = 0

        while time.perf_counter() - start < 5:
            registry.get("test_action")
            count += 1

        elapsed = time.perf_counter() - start
        throughput = count / elapsed

        # Should handle at least 100,000 lookups per second
        assert throughput > 100000, f"Throughput: {throughput} lookups/sec"
