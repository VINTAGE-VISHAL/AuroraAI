import time
from typing import Optional, Iterator, Union, List, Dict
from aurora.inference.interfaces import IInferenceEngine, IModelLoader, IAdapterManager, IGenerator
from aurora.models.inference import GenerationResult
from aurora.registry.module_registry import ModuleRegistry


@ModuleRegistry.register("inference_engine")
class InferenceEngine(IInferenceEngine):
    """Single-pass inference engine combining Qwen3-8B with the Aurora LoRA adapter."""

    def __init__(
        self,
        model_loader: IModelLoader,
        adapter_manager: IAdapterManager,
        generator: IGenerator,
    ) -> None:
        self.model_loader = model_loader
        self.adapter_manager = adapter_manager
        self.generator = generator
        self._initialized = False
        self.last_run_metrics = {}

    @property
    def initialized(self) -> bool:
        return self._initialized

    def initialize(self, model_name: str, trust_remote_code: bool = False) -> None:
        """Loads and caches the base model once."""
        self.model_loader.load(model_name, trust_remote_code=trust_remote_code)
        self._initialized = True

    def generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        adapter_path: Optional[str] = None,
        temperature: float = 0.7,
        max_new_tokens: int = 3072,
        top_p: float = 0.9,
    ) -> GenerationResult:
        """Executes single-pass generative inference using Qwen3-8B (+ optional Aurora LoRA)."""
        if not self._initialized:
            self.initialize("MockModel")

        model, tokenizer = self.model_loader.get_loaded()
        base_load_time = getattr(self.model_loader, "get_load_time", lambda: 0.0)()

        is_peft = False
        try:
            from peft import PeftModel
            if isinstance(model, PeftModel):
                is_peft = True
        except ImportError:
            pass

        log_msg = f"[LOG] Open WebUI messages received: {repr(prompt)}"
        print(log_msg.encode('ascii', 'backslashreplace').decode('ascii'))

        t_start = time.perf_counter()

        if adapter_path:
            # Mount/Activate Aurora LoRA Adapter
            t_start_load = time.perf_counter()
            active_model = self.adapter_manager.set_adapter(model, adapter_path)
            adapter_load_time = time.perf_counter() - t_start_load

            result = self.generator.generate(
                model=active_model,
                tokenizer=tokenizer,
                prompt=prompt,
                temperature=temperature,
                max_new_tokens=max_new_tokens,
                top_p=top_p,
                stage=2,
            )
        else:
            adapter_load_time = 0.0
            if is_peft:
                with model.disable_adapter():
                    result = self.generator.generate(
                        model=model,
                        tokenizer=tokenizer,
                        prompt=prompt,
                        temperature=temperature,
                        max_new_tokens=max_new_tokens,
                        top_p=top_p,
                        stage=2,
                    )
            else:
                result = self.generator.generate(
                    model=model,
                    tokenizer=tokenizer,
                    prompt=prompt,
                    temperature=temperature,
                    max_new_tokens=max_new_tokens,
                    top_p=top_p,
                    stage=2,
                )

        duration = time.perf_counter() - t_start

        self.last_run_metrics = {
            "base_load_time": base_load_time,
            "adapter_load_time": adapter_load_time,
            "generation_time": result.generation_time,
            "tokens_generated": result.tokens_generated,
            "tokens_per_second": result.tokens_per_second,
            "total_time": duration,
        }

        return GenerationResult(
            answer=result.answer,
            generation_time=duration,
            tokens_generated=result.tokens_generated,
            tokens_per_second=result.tokens_generated / duration if duration > 0 else 0.0,
            base_load_time=base_load_time,
            adapter_load_time=adapter_load_time,
        )

    def generate_stream(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        adapter_path: Optional[str] = None,
        temperature: float = 0.7,
        max_new_tokens: int = 3072,
        top_p: float = 0.9,
    ) -> Iterator[str]:
        """Streams tokens in real-time from single-pass inference."""
        if not self._initialized:
            self.initialize("MockModel")

        model, tokenizer = self.model_loader.get_loaded()
        base_load_time = getattr(self.model_loader, "get_load_time", lambda: 0.0)()

        is_peft = False
        try:
            from peft import PeftModel
            if isinstance(model, PeftModel):
                is_peft = True
        except ImportError:
            pass

        log_msg = f"[LOG] Open WebUI messages received: {repr(prompt)}"
        print(log_msg.encode('ascii', 'backslashreplace').decode('ascii'))

        t_start = time.perf_counter()
        tokens_count = 0

        if adapter_path:
            t_start_load = time.perf_counter()
            active_model = self.adapter_manager.set_adapter(model, adapter_path)
            adapter_load_time = time.perf_counter() - t_start_load

            try:
                for chunk in self.generator.generate_stream(
                    model=active_model,
                    tokenizer=tokenizer,
                    prompt=prompt,
                    temperature=temperature,
                    max_new_tokens=max_new_tokens,
                    top_p=top_p,
                    stage=2,
                ):
                    tokens_count += len(chunk.split())
                    yield chunk
            finally:
                duration = time.perf_counter() - t_start
                self.last_run_metrics = {
                    "base_load_time": base_load_time,
                    "adapter_load_time": adapter_load_time,
                    "generation_time": duration,
                    "tokens_generated": tokens_count,
                    "tokens_per_second": tokens_count / duration if duration > 0 else 0.0,
                    "total_time": duration,
                }
        else:
            adapter_load_time = 0.0
            try:
                if is_peft:
                    with model.disable_adapter():
                        for chunk in self.generator.generate_stream(
                            model=model,
                            tokenizer=tokenizer,
                            prompt=prompt,
                            temperature=temperature,
                            max_new_tokens=max_new_tokens,
                            top_p=top_p,
                            stage=2,
                        ):
                            tokens_count += len(chunk.split())
                            yield chunk
                else:
                    for chunk in self.generator.generate_stream(
                        model=model,
                        tokenizer=tokenizer,
                        prompt=prompt,
                        temperature=temperature,
                        max_new_tokens=max_new_tokens,
                        top_p=top_p,
                        stage=2,
                    ):
                        tokens_count += len(chunk.split())
                        yield chunk
            finally:
                duration = time.perf_counter() - t_start
                self.last_run_metrics = {
                    "base_load_time": base_load_time,
                    "adapter_load_time": 0.0,
                    "generation_time": duration,
                    "tokens_generated": tokens_count,
                    "tokens_per_second": tokens_count / duration if duration > 0 else 0.0,
                    "total_time": duration,
                }
