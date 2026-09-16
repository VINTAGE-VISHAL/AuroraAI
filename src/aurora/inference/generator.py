"""Generator implementation for causal sequence decoding and performance benchmarks."""

import time
from typing import Any, Iterator
from aurora.core.exceptions import InterfaceError
from aurora.inference.interfaces import IGenerator
from aurora.models.inference import GenerationResult
from aurora.registry.module_registry import ModuleRegistry

# Conditional torch import
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


@ModuleRegistry.register("generator")
class Generator(IGenerator):
    """Executes prompt encoding, causal token generation, and performance throughput logging."""

    def generate(
        self,
        model: Any,
        tokenizer: Any,
        prompt: Any,
        temperature: float = 0.7,
        max_new_tokens: int = 3072,
        top_p: float = 0.9,
        stage: int = 2,
    ) -> GenerationResult:
        """Tokenizes prompt, runs causal generative inference, and records metrics."""
        if not HAS_TORCH or type(model).__name__ == "MockModelObj" or hasattr(model, "is_mock"):
            return self._generate_mock(prompt)

        try:
            start_time = time.perf_counter()

            # Apply chat template if supported by tokenizer
            if hasattr(tokenizer, "apply_chat_template"):
                if isinstance(prompt, list):
                    messages = prompt
                else:
                    messages = [
                        {"role": "user", "content": prompt}
                    ]
                try:
                    formatted_prompt = tokenizer.apply_chat_template(
                        messages,
                        tokenize=False,
                        add_generation_prompt=True,
                    )
                except Exception:
                    formatted_prompt = prompt
            else:
                formatted_prompt = prompt

            device = "cpu"
            if torch.cuda.is_available():
                device = "cuda"
            elif hasattr(model, "device"):
                device = model.device
            else:
                try:
                    p_device = next(model.parameters()).device
                    if str(p_device) != "meta":
                        device = p_device
                except Exception:
                    pass

            # Encode input prompt
            inputs = tokenizer(formatted_prompt, return_tensors="pt")
            input_ids = inputs["input_ids"].to(device)
            attention_mask = inputs.get("attention_mask", None)
            if attention_mask is not None:
                attention_mask = attention_mask.to(device)

            stop_token_ids = [tokenizer.eos_token_id]
            if tokenizer.pad_token_id is not None:
                stop_token_ids.append(tokenizer.pad_token_id)

            gen_kwargs = {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "max_new_tokens": max_new_tokens,
                "pad_token_id": tokenizer.pad_token_id or tokenizer.eos_token_id,
                "eos_token_id": stop_token_ids,
            }
            if temperature > 0.0:
                gen_kwargs["do_sample"] = True
                gen_kwargs["temperature"] = temperature
                gen_kwargs["top_p"] = top_p
            else:
                gen_kwargs["do_sample"] = False

            log_msg = f"[LOG] Compiled input: {repr(formatted_prompt)}"
            print(log_msg.encode('ascii', 'backslashreplace').decode('ascii'))

            # Execute model generation
            with torch.no_grad():
                if torch.cuda.is_available():
                    with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                        output_ids = model.generate(**gen_kwargs)
                else:
                    output_ids = model.generate(**gen_kwargs)
            print("Generation finished.")

            end_time = time.perf_counter()
            duration = end_time - start_time

            # Decode only newly generated tokens
            generated_ids = output_ids[0][len(input_ids[0]):]
            answer = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

            tokens_count = len(generated_ids)
            tps = tokens_count / duration if duration > 0 else 0.0

            # Log termination diagnostics
            reached_max = tokens_count >= max_new_tokens
            term_reason = "max_tokens_reached" if reached_max else "natural_eos"
            diag_msg = f"[LOG] Diagnostics: generated_tokens={tokens_count}, max_new_tokens={max_new_tokens}, eos_token_id={tokenizer.eos_token_id}, reached_max_tokens={reached_max}, termination_reason={term_reason}"
            print(diag_msg.encode('ascii', 'backslashreplace').decode('ascii'))

            return GenerationResult(
                answer=answer,
                generation_time=duration,
                tokens_generated=tokens_count,
                tokens_per_second=tps,
            )

        except Exception as e:
            raise InterfaceError(f"Generator failed to execute causal generation: {e}") from e

    def _generate_mock(self, prompt: Any) -> GenerationResult:
        """Simulates response generation for unit testing without GPU runtime."""
        start_time = time.perf_counter()
        time.sleep(0.1)
        answer = f"Mock response generated for prompt: '{prompt}'"
        duration = time.perf_counter() - start_time
        tokens_count = len(answer.split())
        tps = tokens_count / duration if duration > 0 else 0.0

        return GenerationResult(
            answer=answer,
            generation_time=duration,
            tokens_generated=tokens_count,
            tokens_per_second=tps,
        )

    def generate_stream(
        self,
        model: Any,
        tokenizer: Any,
        prompt: Any,
        temperature: float = 0.7,
        max_new_tokens: int = 3072,
        top_p: float = 0.9,
        stage: int = 2,
    ) -> Iterator[str]:
        """Streams generated tokens in real-time using TextIteratorStreamer."""
        if not HAS_TORCH or type(model).__name__ == "MockModelObj" or hasattr(model, "is_mock"):
            yield from self._generate_stream_mock(prompt)
            return

        try:
            from transformers import TextIteratorStreamer
            from threading import Thread

            if hasattr(tokenizer, "apply_chat_template"):
                if isinstance(prompt, list):
                    messages = prompt
                else:
                    messages = [
                        {"role": "user", "content": prompt}
                    ]
                try:
                    formatted_prompt = tokenizer.apply_chat_template(
                        messages,
                        tokenize=False,
                        add_generation_prompt=True,
                    )
                except Exception:
                    formatted_prompt = prompt
            else:
                formatted_prompt = prompt

            device = "cpu"
            if torch.cuda.is_available():
                device = "cuda"
            elif hasattr(model, "device"):
                device = model.device

            inputs = tokenizer(formatted_prompt, return_tensors="pt")
            input_ids = inputs["input_ids"].to(device)
            attention_mask = inputs.get("attention_mask", None)
            if attention_mask is not None:
                attention_mask = attention_mask.to(device)

            log_msg = f"[LOG] Compiled streaming input: {repr(formatted_prompt)}"
            print(log_msg.encode('ascii', 'backslashreplace').decode('ascii'))

            streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)

            stop_token_ids = [tokenizer.eos_token_id]
            if tokenizer.pad_token_id is not None:
                stop_token_ids.append(tokenizer.pad_token_id)

            gen_kwargs = {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "max_new_tokens": max_new_tokens,
                "pad_token_id": tokenizer.pad_token_id or tokenizer.eos_token_id,
                "eos_token_id": stop_token_ids,
                "use_cache": True,
                "streamer": streamer,
            }
            if temperature > 0.0:
                gen_kwargs["do_sample"] = True
                gen_kwargs["temperature"] = temperature
                gen_kwargs["top_p"] = top_p
            else:
                gen_kwargs["do_sample"] = False

            start_time = time.perf_counter()

            # Launch generation thread using inference_mode for maximum speed
            def generate_with_autocast(**kwargs):
                with torch.inference_mode():
                    if torch.cuda.is_available():
                        with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                            model.generate(**kwargs)
                    else:
                        model.generate(**kwargs)

            thread = Thread(target=generate_with_autocast, kwargs=gen_kwargs)
            thread.start()

            tokens_count = 0
            for new_text in streamer:
                elapsed = time.perf_counter() - start_time
                log_msg = f"[{elapsed:.2f}s] [Stream Chunk]: {repr(new_text)}"
                print(log_msg.encode('ascii', 'backslashreplace').decode('ascii'))
                
                # Count tokens of yielded text
                chunk_tokens = len(tokenizer.encode(new_text, add_special_tokens=False))
                tokens_count += chunk_tokens
                yield new_text

            thread.join()

            reached_max = tokens_count >= max_new_tokens
            term_reason = "max_tokens_reached" if reached_max else "natural_eos"
            diag_msg = f"[LOG] Diagnostics (Stream): generated_tokens={tokens_count}, max_new_tokens={max_new_tokens}, eos_token_id={tokenizer.eos_token_id}, reached_max_tokens={reached_max}, termination_reason={term_reason}"
            print(diag_msg.encode('ascii', 'backslashreplace').decode('ascii'))

        except Exception as e:
            raise InterfaceError(f"Streaming generation failed: {e}") from e

    def _generate_stream_mock(self, prompt: Any) -> Iterator[str]:
        """Simulates streaming response chunks with timing sleep cycles."""
        full_text = f"Mock response generated for prompt: '{prompt}'"
        for word in full_text.split(" "):
            yield word + " "
            time.sleep(0.02)
