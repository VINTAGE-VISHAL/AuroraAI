"""Unit tests for Phase E Inference Engine subsystem."""

import pytest
from aurora.inference.interfaces import IModelLoader, IAdapterManager, IGenerator, IInferenceEngine
from aurora.inference.loader import ModelLoader
from aurora.inference.adapter_manager import AdapterManager
from aurora.inference.generator import Generator
from aurora.inference.inference_engine import InferenceEngine
from aurora.models.inference import GenerationResult


def test_model_loader_singleton() -> None:
    """Verify that ModelLoader behaves as a Singleton caching instances."""
    loader1 = ModelLoader()
    loader2 = ModelLoader()
    assert loader1 is loader2

    m1, t1 = loader1.load("MockModel")
    m2, t2 = loader2.load("MockModel")

    assert m1 is m2
    assert t1 is t2


def test_adapter_manager_switching() -> None:
    """Verify that AdapterManager correctly sets and unloads adapter metadata properties."""
    loader = ModelLoader()
    model, _ = loader.load("MockModel")

    manager = AdapterManager()
    
    # Test setting adapter
    wrapped_model = manager.set_adapter(model, "/path/to/adapter")
    assert manager.get_current_adapter() == "/path/to/adapter"
    assert wrapped_model.active_adapter == "/path/to/adapter"

    # Test unloading adapter
    unloaded_model = manager.unload_adapter(wrapped_model)
    assert manager.get_current_adapter() == ""
    assert not hasattr(unloaded_model, "active_adapter")


def test_generator_metrics() -> None:
    """Verify that Generator produces correct performance stats and formats."""
    loader = ModelLoader()
    model, tokenizer = loader.load("MockModel")

    generator = Generator()
    result = generator.generate(model, tokenizer, "Test prompt")

    assert isinstance(result, GenerationResult)
    assert "Mock response generated" in result.answer
    assert result.generation_time > 0
    assert result.tokens_generated > 0
    assert result.tokens_per_second > 0


def test_inference_engine_coordination() -> None:
    """Verify that InferenceEngine orchestrates model loading, adapter swaps, and generation."""
    loader = ModelLoader()
    manager = AdapterManager()
    gen = Generator()

    engine = InferenceEngine(loader, manager, gen)
    engine.initialize("MockModel")

    result = engine.generate("Predictive index query", adapter_path="/adapters/dbms")

    assert isinstance(result, GenerationResult)
    assert manager.get_current_adapter() == "/adapters/dbms"
    assert "Predictive index query" in result.answer


def test_generator_streaming() -> None:
    """Verify that Generator.generate_stream correctly yields text chunks."""
    loader = ModelLoader()
    model, tokenizer = loader.load("MockModel")

    generator = Generator()
    chunks = list(generator.generate_stream(model, tokenizer, "DBMS query"))
    
    assert len(chunks) > 0
    full_text = "".join(chunks)
    assert "Mock response generated" in full_text


def test_inference_engine_streaming() -> None:
    """Verify that InferenceEngine coordinates streaming generation correctly."""
    loader = ModelLoader()
    manager = AdapterManager()
    gen = Generator()

    engine = InferenceEngine(loader, manager, gen)
    engine.initialize("MockModel")

    chunks = list(engine.generate_stream("SQL index", adapter_path="/adapters/dbms"))
    assert len(chunks) > 0
    full_text = "".join(chunks)
    assert "SQL index" in full_text
    assert manager.get_current_adapter() == "/adapters/dbms"
