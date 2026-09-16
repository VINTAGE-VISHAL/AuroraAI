"""Streamlit-based Aurora Evaluation Lab Application."""

import datetime
import json
import os
import time
import streamlit as st

from aurora.inference.loader import ModelLoader
from aurora.inference.adapter_manager import AdapterManager
from aurora.inference.generator import Generator
from aurora.inference.inference_engine import InferenceEngine
from aurora.models.inference import GenerationResult

# Set premium styled UI theme configuration
st.set_page_config(
    page_title="Aurora Evaluation Lab",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom premium styling via HSL tailored dark mode colors and glassmorphism elements
st.markdown(
    """
    <style>
    /* Dark Theme Core Styles */
    .stApp {
        background-color: #0b0c10;
        color: #c5c6c7;
        font-family: 'Inter', -apple-system, sans-serif;
    }
    h1, h2, h3 {
        color: #66fcf1 !important;
        font-weight: 700;
        letter-spacing: -0.025em;
    }
    .stSidebar {
        background-color: #1f2833 !important;
        border-right: 1px solid #45f3ff33;
    }
    
    /* Sleek card elements */
    .metric-card {
        background: rgba(31, 40, 51, 0.45);
        border: 1px solid rgba(102, 252, 241, 0.25);
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        transition: all 0.25s ease;
    }
    .metric-card:hover {
        border-color: rgba(102, 252, 241, 0.6);
        box-shadow: 0 4px 12px rgba(102, 252, 241, 0.15);
    }
    .response-card {
        background: #1f2833;
        border: 1px solid #45f3ff44;
        border-radius: 12px;
        padding: 20px;
        color: #ffffff;
        margin: 15px 0;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_inference_engine(model_name: str) -> InferenceEngine:
    """Caching model instantiation so it stays alive between query runs."""
    loader = ModelLoader()
    manager = AdapterManager()
    gen = Generator()
    engine = InferenceEngine(loader, manager, gen)
    engine.initialize(model_name)
    return engine


def log_interaction(
    prompt: str,
    model_mode: str,
    result: GenerationResult,
    adapter_path: str = "",
) -> None:
    """Appends model queries and performance statistics to persistent daily jsonl logs."""
    log_dir = "data/logs"
    os.makedirs(log_dir, exist_ok=True)
    
    today = datetime.date.today().isoformat()
    log_file = os.path.join(log_dir, f"{today}.jsonl")
    
    record = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "prompt": prompt,
        "mode": model_mode,
        "adapter_path": adapter_path,
        "answer": result.answer,
        "generation_time": result.generation_time,
        "tokens_generated": result.tokens_generated,
        "tokens_per_second": result.tokens_per_second,
    }
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def parse_stream_content(full_text: str):
    """Parses streaming response text to extract the think block and final answer."""
    if "<think>" in full_text:
        parts = full_text.split("<think>", 1)
        prefix = parts[0]
        rest = parts[1]
        
        if "</think>" in rest:
            think_parts = rest.split("</think>", 1)
            reasoning = think_parts[0].strip()
            answer = think_parts[1].strip()
            return reasoning, answer, True
        else:
            reasoning = rest.strip()
            return reasoning, "", False
    else:
        # Fallback for models without think tags
        return "", full_text.strip(), True


def main() -> None:
    # 1. Main header and subtitle
    st.title("🧬 Aurora Evaluation Lab")
    st.markdown("Scientific comparison environment comparing Base Models vs. custom LoRA Adapter specializations.")
    st.write("---")

    # 2. Sidebar configuration panel
    st.sidebar.header("🧪 Lab Configuration")
    
    model_repo = st.sidebar.text_input(
        "Base Model Repository",
        value="Qwen/Qwen3-8B",
        help="Specify HF Repository identifier or 'MockModel' for dry-runs.",
    )
    
    adapter_path = st.sidebar.text_input(
        "LoRA Adapter Path",
        value="C:/AuroraEngine/data/output/stage1_smoke_test/final_adapter",
        help="Local directory location containing model adapter weights.",
    )
    
    st.sidebar.subheader("🎛️ Decoding Hyperparameters")
    temperature = st.sidebar.slider("Temperature", 0.0, 1.2, 0.7, step=0.1)
    max_new_tokens = st.sidebar.slider("Max New Tokens", 16, 2048, 1024, step=16)
    top_p = st.sidebar.slider("Top P", 0.1, 1.0, 0.8, step=0.05)

    # 3. Model Engine initialization
    try:
        engine = get_inference_engine(model_repo)
    except Exception as e:
        st.error(f"Inference Engine startup failure: {e}")
        return

    # 4. Mode Selection Layout tabs
    mode = st.radio(
        "Evaluation Mode Selection:",
        options=["Base Model Only", "Aurora (Base + LoRA)", "Compare Mode (Side-by-Side)"],
        horizontal=True,
    )
    
    st.write("")
    
    # 5. Question/Prompt Input panel
    prompt = st.text_area(
        "Enter Inquiry / Prompt:",
        placeholder="Type a technical DBMS query (e.g. explain relational algebra principles)...",
        height=150,
    )
    
    col_ask, _ = st.columns([1, 6])
    with col_ask:
        run_btn = st.button("🧬 Run Evaluation", use_container_width=True)

    if run_btn and prompt.strip():
        st.write("---")
        
        # Mode 1: Base Model Only
        if mode == "Base Model Only":
            st.subheader("🤖 Base Model Response")
            
            placeholder_think = st.empty()
            placeholder_answer = st.empty()
            full_text = ""
            start_t = time.perf_counter()
            
            stream_gen = engine.generate_stream(
                prompt=prompt,
                adapter_path="",
                temperature=temperature,
                max_new_tokens=max_new_tokens,
                top_p=top_p,
            )
            
            last_update = time.perf_counter()
            for chunk in stream_gen:
                full_text += chunk
                
                # Rate limit UI renders to once every 50ms to prevent backpressure bottlenecks
                if time.perf_counter() - last_update >= 0.05:
                    reasoning, answer, finished_thinking = parse_stream_content(full_text)
                    if reasoning:
                        status_text = "Thought Process (Complete)" if finished_thinking else "Thinking..."
                        placeholder_think.markdown(
                            f"""
                            <details open>
                                <summary style='color: #66fcf1; cursor: pointer; font-weight: bold;'>🧠 {status_text}</summary>
                                <div style='background: rgba(102, 252, 241, 0.05); border-left: 3px solid #66fcf1; padding: 10px; margin-top: 5px; font-family: monospace; white-space: pre-wrap; color: #a9a9a9;'>
                                    {reasoning}
                                </div>
                            </details>
                            """,
                            unsafe_allow_html=True
                        )
                    if answer:
                        placeholder_answer.markdown(f"<div class='response-card'>{answer}▋</div>", unsafe_allow_html=True)
                    elif finished_thinking:
                        placeholder_answer.markdown(f"<div class='response-card'>▋</div>", unsafe_allow_html=True)
                    last_update = time.perf_counter()
                
            duration = time.perf_counter() - start_t
            reasoning, answer, _ = parse_stream_content(full_text)
            
            if reasoning:
                placeholder_think.markdown(
                    f"""
                    <details>
                        <summary style='color: #66fcf1; cursor: pointer; font-weight: bold;'>🧠 Thought Process</summary>
                        <div style='background: rgba(102, 252, 241, 0.05); border-left: 3px solid #66fcf1; padding: 10px; margin-top: 5px; font-family: monospace; white-space: pre-wrap; color: #a9a9a9;'>
                            {reasoning}
                        </div>
                    </details>
                    """,
                    unsafe_allow_html=True
                )
            placeholder_answer.markdown(f"<div class='response-card'>{answer}</div>", unsafe_allow_html=True)
            
            tokens_count = len(full_text.split())
            tps = tokens_count / duration if duration > 0 else 0.0
            res = GenerationResult(
                answer=answer,
                generation_time=duration,
                tokens_generated=tokens_count,
                tokens_per_second=tps,
            )
            
            # Show Metrics Card
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"<div class='metric-card'><b>Speed:</b> {res.tokens_per_second:.2f} tokens/sec</div>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<div class='metric-card'><b>Duration:</b> {res.generation_time:.3f} seconds</div>", unsafe_allow_html=True)
            with col3:
                st.markdown(f"<div class='metric-card'><b>Tokens:</b> {res.tokens_generated} generated</div>", unsafe_allow_html=True)
                
            log_interaction(prompt, "base_only", res)

        # Mode 2: Aurora Model Only
        elif mode == "Aurora (Base + LoRA)":
            st.subheader("🛡️ Aurora Specialized Response")
            
            placeholder_think = st.empty()
            placeholder_answer = st.empty()
            full_text = ""
            start_t = time.perf_counter()
            
            stream_gen = engine.generate_stream(
                prompt=prompt,
                adapter_path=adapter_path,
                temperature=temperature,
                max_new_tokens=max_new_tokens,
                top_p=top_p,
            )
            
            # Show a spinner during Stage 1 specialist query and first token synthesis
            with st.spinner("Querying Specialist LoRA & Synthesizing..."):
                try:
                    first_chunk = next(stream_gen)
                    full_text += first_chunk
                except StopIteration:
                    first_chunk = None

            t_ui_stream_start = time.perf_counter()
            if first_chunk is not None:
                last_update = time.perf_counter()
                for chunk in stream_gen:
                    full_text += chunk
                    
                    # Rate limit UI renders to once every 50ms to prevent backpressure bottlenecks
                    if time.perf_counter() - last_update >= 0.05:
                        reasoning, answer, finished_thinking = parse_stream_content(full_text)
                    
                        if reasoning:
                            status_text = "Thought Process (Complete)" if finished_thinking else "Thinking..."
                            placeholder_think.markdown(
                                f"""
                                <details open>
                                    <summary style='color: #66fcf1; cursor: pointer; font-weight: bold;'>🧠 {status_text}</summary>
                                    <div style='background: rgba(102, 252, 241, 0.05); border-left: 3px solid #66fcf1; padding: 10px; margin-top: 5px; font-family: monospace; white-space: pre-wrap; color: #a9a9a9;'>
                                        {reasoning}
                                    </div>
                                </details>
                                """,
                                unsafe_allow_html=True
                            )
                        if answer:
                            placeholder_answer.markdown(f"<div class='response-card'>{answer}▋</div>", unsafe_allow_html=True)
                        elif finished_thinking:
                            placeholder_answer.markdown(f"<div class='response-card'>▋</div>", unsafe_allow_html=True)
                        last_update = time.perf_counter()
            t_ui_stream_end = time.perf_counter()
            ui_stream_time = t_ui_stream_end - t_ui_stream_start
                
            duration = time.perf_counter() - start_t
            reasoning, answer, _ = parse_stream_content(full_text)
            
            if reasoning:
                placeholder_think.markdown(
                    f"""
                    <details>
                        <summary style='color: #66fcf1; cursor: pointer; font-weight: bold;'>🧠 Thought Process</summary>
                        <div style='background: rgba(102, 252, 241, 0.05); border-left: 3px solid #66fcf1; padding: 10px; margin-top: 5px; font-family: monospace; white-space: pre-wrap; color: #a9a9a9;'>
                            {reasoning}
                        </div>
                    </details>
                    """,
                    unsafe_allow_html=True
                )
            placeholder_answer.markdown(f"<div class='response-card'>{answer}</div>", unsafe_allow_html=True)
            
            tokens_count = len(full_text.split())
            tps = tokens_count / duration if duration > 0 else 0.0
            res = GenerationResult(
                answer=answer,
                generation_time=duration,
                tokens_generated=tokens_count,
                tokens_per_second=tps,
            )
            
            # Retrieve backend instrumented timings
            metrics = getattr(engine, "last_run_metrics", {})
            base_load_time = metrics.get("base_load_time", 0.0)
            adapter_load_time = metrics.get("adapter_load_time", 0.0)
            specialist_gen_time = metrics.get("specialist_gen_time", 0.0)
            specialist_tokens = metrics.get("specialist_tokens", 0)
            specialist_tps = metrics.get("specialist_tps", 0.0)
            adapter_unload_time = metrics.get("adapter_unload_time", 0.0)
            vanilla_gen_time = metrics.get("vanilla_gen_time", 0.0)
            vanilla_tokens = metrics.get("vanilla_tokens", 0)
            vanilla_tps = metrics.get("vanilla_tps", 0.0)
            total_pipeline_time = metrics.get("total_time", 0.0)

            # Show Detailed Latency Instrumentation Table
            st.markdown("### ⏱️ Granular Pipeline Diagnostics")
            st.markdown(
                f"""
                <div style='background-color: #1a1a24; border: 1px solid #333; padding: 15px; border-radius: 8px; margin-top: 15px;'>
                    <table style='width:100%; border-collapse: collapse; font-family: monospace; font-size: 14px; color: #dcdcdc;'>
                        <tr style='border-bottom: 2px solid #66fcf1; color: #66fcf1; font-weight: bold;'>
                            <th style='text-align: left; padding: 8px;'>Pipeline Step</th>
                            <th style='text-align: right; padding: 8px;'>Duration</th>
                            <th style='text-align: right; padding: 8px;'>Details</th>
                        </tr>
                        <tr style='border-bottom: 1px solid #222;'>
                            <td style='padding: 8px;'>1. Base Model Load</td>
                            <td style='text-align: right; padding: 8px; color: #ffc107;'>{base_load_time:.3f} s</td>
                            <td style='text-align: right; padding: 8px; color: #888;'>Cold start load</td>
                        </tr>
                        <tr style='border-bottom: 1px solid #222;'>
                            <td style='padding: 8px;'>2. PEFT LoRA Load</td>
                            <td style='text-align: right; padding: 8px; color: #ff5722;'>{adapter_load_time:.3f} s</td>
                            <td style='text-align: right; padding: 8px; color: #888;'>SWAP IN adapter</td>
                        </tr>
                        <tr style='border-bottom: 1px solid #222;'>
                            <td style='padding: 8px;'>3. Stage 1 Specialist Gen</td>
                            <td style='text-align: right; padding: 8px; color: #ff5722;'>{specialist_gen_time:.3f} s</td>
                            <td style='text-align: right; padding: 8px; color: #888;'>{specialist_tokens} tokens ({specialist_tps:.2f} t/s)</td>
                        </tr>
                        <tr style='border-bottom: 1px solid #222;'>
                            <td style='padding: 8px;'>4. PEFT LoRA Unload</td>
                            <td style='text-align: right; padding: 8px; color: #ff5722;'>{adapter_unload_time:.3f} s</td>
                            <td style='text-align: right; padding: 8px; color: #888;'>SWAP OUT adapter</td>
                        </tr>
                        <tr style='border-bottom: 1px solid #222;'>
                            <td style='padding: 8px;'>5. Stage 2 Vanilla Gen</td>
                            <td style='text-align: right; padding: 8px; color: #2196f3;'>{vanilla_gen_time:.3f} s</td>
                            <td style='text-align: right; padding: 8px; color: #888;'>{vanilla_tokens} tokens ({vanilla_tps:.2f} t/s)</td>
                        </tr>
                        <tr style='border-bottom: 2px solid #66fcf1;'>
                            <td style='padding: 8px;'>6. UI Stream / Render</td>
                            <td style='text-align: right; padding: 8px; color: #4caf50;'>{ui_stream_time:.3f} s</td>
                            <td style='text-align: right; padding: 8px; color: #888;'>Websocket + draw time</td>
                        </tr>
                        <tr style='font-weight: bold; font-size: 15px; color: #66fcf1;'>
                            <td style='padding: 10px 8px 0 8px;'>Total System Latency</td>
                            <td style='text-align: right; padding: 10px 8px 0 8px;'>{duration:.3f} s</td>
                            <td style='text-align: right; padding: 10px 8px 0 8px;'>Combined stack duration</td>
                        </tr>
                    </table>
                </div>
                """,
                unsafe_allow_html=True
            )
                
            log_interaction(prompt, "aurora_lora", res, adapter_path)

        # Mode 3: Compare Mode (Side-by-Side)
        else:
            st.subheader("🆚 Comparative Layout Analysis")
            
            col_base, col_aurora = st.columns(2)
            
            # Base generation
            with col_base:
                st.markdown("#### 🤖 Base Model")
                with st.spinner("Generating base model answer..."):
                    res_base = engine.generate(
                        prompt=prompt,
                        adapter_path="",
                        temperature=temperature,
                        max_new_tokens=max_new_tokens,
                        top_p=top_p,
                    )
                reasoning_base, answer_base, _ = parse_stream_content(res_base.answer)
                if reasoning_base:
                    st.markdown(
                        f"""
                        <details>
                            <summary style='color: #66fcf1; cursor: pointer; font-weight: bold;'>🧠 Thought Process</summary>
                            <div style='background: rgba(102, 252, 241, 0.05); border-left: 3px solid #66fcf1; padding: 10px; margin-top: 5px; font-family: monospace; white-space: pre-wrap; color: #a9a9a9;'>
                                {reasoning_base}
                            </div>
                        </details>
                        """,
                        unsafe_allow_html=True
                    )
                st.markdown(f"<div class='response-card'>{answer_base}</div>", unsafe_allow_html=True)
                
                # Base metrics
                st.markdown(
                    f"""
                    <div class='metric-card'>
                        <b>Throughput:</b> {res_base.tokens_per_second:.2f} t/s<br>
                        <b>Latency:</b> {res_base.generation_time:.3f} s<br>
                        <b>Tokens:</b> {res_base.tokens_generated}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                log_interaction(prompt, "compare_base", res_base)

            # Aurora generation
            with col_aurora:
                st.markdown("#### 🛡️ Aurora Specialized (LoRA)")
                with st.spinner("Applying LoRA adapter and generating..."):
                    res_aurora = engine.generate(
                        prompt=prompt,
                        adapter_path=adapter_path,
                        temperature=temperature,
                        max_new_tokens=max_new_tokens,
                        top_p=top_p,
                    )
                reasoning_aurora, answer_aurora, _ = parse_stream_content(res_aurora.answer)
                if reasoning_aurora:
                    st.markdown(
                        f"""
                        <details>
                            <summary style='color: #66fcf1; cursor: pointer; font-weight: bold;'>🧠 Thought Process</summary>
                            <div style='background: rgba(102, 252, 241, 0.05); border-left: 3px solid #66fcf1; padding: 10px; margin-top: 5px; font-family: monospace; white-space: pre-wrap; color: #a9a9a9;'>
                                {reasoning_aurora}
                            </div>
                        </details>
                        """,
                        unsafe_allow_html=True
                    )
                st.markdown(f"<div class='response-card'>{answer_aurora}</div>", unsafe_allow_html=True)
                
                # Aurora metrics
                st.markdown(
                    f"""
                    <div class='metric-card'>
                        <b>Throughput:</b> {res_aurora.tokens_per_second:.2f} t/s<br>
                        <b>Latency:</b> {res_aurora.generation_time:.3f} s<br>
                        <b>Tokens:</b> {res_aurora.tokens_generated}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                log_interaction(prompt, "compare_aurora", res_aurora, adapter_path)
                
            # Quick summary benchmark comparison card
            st.write("")
            st.subheader("📊 Performance Speed Delta")
            speed_ratio = res_aurora.tokens_per_second / res_base.tokens_per_second if res_base.tokens_per_second > 0 else 1.0
            st.info(f"Aurora generated tokens at **{speed_ratio:.2f}x** the throughput speed of the raw Base Model.")


if __name__ == "__main__":
    main()
