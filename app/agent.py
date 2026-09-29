from __future__ import annotations

import os
import time
from dataclasses import dataclass

from . import metrics
from .mock_llm import FakeLLM
from .mock_rag import retrieve
from .pii import hash_user_id, summarize_text
from .prompt_management import resolve_prompt
from .tracing import (
    get_langfuse_client,
    mark_error,
    observe,
    propagate_attributes,
    tracing_enabled,
    update_generation,
    update_span,
)


@dataclass
class AgentResult:
    answer: str
    latency_ms: int
    ttft_ms: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    quality_score: float


class LabAgent:
    # Đơn giá tham chiếu (USD / 1M token) dùng cho cả log lẫn trace để
    # dashboard và Langfuse không lệch số cost với nhau.
    INPUT_COST_PER_MTOK = 3.0
    OUTPUT_COST_PER_MTOK = 15.0

    def __init__(self, model: str = "claude-sonnet-4-5") -> None:
        self.model = model
        self.llm = FakeLLM(model=model)

    @observe(name="lab-agent-run", as_type="agent", capture_input=False, capture_output=False)
    def run(
        self,
        user_id: str,
        feature: str,
        session_id: str,
        message: str,
        correlation_id: str,
    ) -> AgentResult:
        langfuse_client = get_langfuse_client()
        with propagate_attributes(
            user_id=hash_user_id(user_id),
            session_id=session_id,
            tags=["lab", feature, self.model],
            trace_name="day13-agent-request",
            environment=os.getenv("APP_ENV", "dev"),
            metadata={
                "feature": feature,
                "model": self.model,
                "correlation_id": correlation_id,
            },
        ):
            started = time.perf_counter()

            # 1. Instrument retrieve() dưới dạng Child Span (retriever).
            # capture_input/output=False để không đẩy raw query (có thể chứa PII)
            # lên Langfuse; chỉ ghi preview đã scrub.
            @observe(
                name="rag-retrieve",
                as_type="retriever",
                capture_input=False,
                capture_output=False,
            )
            def _instrumented_retrieve(query: str):
                try:
                    return retrieve(query)
                except Exception as exc:
                    mark_error(langfuse_client, message=f"retrieval failed: {type(exc).__name__}")
                    raise

            docs = _instrumented_retrieve(message)
            query_preview = summarize_text(message)
            update_span(
                langfuse_client,
                metadata={
                    "doc_count": len(docs),
                    "query_preview": query_preview,
                },
            )

            # Resolve Prompt từ Langfuse
            prompt = resolve_prompt(
                langfuse_client,
                feature=feature,
                docs=docs,
                message=message,
                enabled=tracing_enabled(),
            )

            # 2. Instrument FakeLLM.generate() dưới dạng Child Generation Observation.
            # Generation phải có model + usage + cost để dashboard tính được cost/token.
            @observe(
                name="llm-generate",
                as_type="generation",
                capture_input=False,
                capture_output=False,
            )
            def _instrumented_generate(prompt_text: str):
                try:
                    return self.llm.generate(prompt_text)
                except Exception as exc:
                    mark_error(
                        langfuse_client,
                        message=f"llm failed: {type(exc).__name__}",
                        generation=True,
                    )
                    raise

            with propagate_attributes(prompt=prompt.managed_prompt):
                response = _instrumented_generate(prompt.text)
                # cost tính ngay từ usage để gắn vào generation observation;
                # Langfuse dùng cost_details này để tổng hợp cost theo trace.
                generation_cost = self._estimate_cost(
                    response.usage.input_tokens, response.usage.output_tokens
                )
                update_generation(
                    langfuse_client,
                    model=response.model,
                    usage_details={
                        "input": response.usage.input_tokens,
                        "output": response.usage.output_tokens,
                        "total": response.usage.input_tokens + response.usage.output_tokens,
                    },
                    cost_details={
                        "input": round(
                            (response.usage.input_tokens / 1_000_000) * self.INPUT_COST_PER_MTOK,
                            8,
                        ),
                        "output": round(
                            (response.usage.output_tokens / 1_000_000) * self.OUTPUT_COST_PER_MTOK,
                            8,
                        ),
                        "total": generation_cost,
                    },
                    metadata={
                        "ttft_ms": response.ttft_ms,
                        "prompt_name": prompt.name,
                        "prompt_label": prompt.label,
                        "prompt_version": prompt.version,
                        "prompt_source": prompt.source,
                    },
                )

            # Tính toán chất lượng, thời gian đáp ứng và chi phí
            quality_score = self._heuristic_quality(message, response.text, docs)
            latency_ms = int((time.perf_counter() - started) * 1000)
            cost_usd = generation_cost

            # 3. Gắn prompt version lên root span. Token/cost đã nằm ở
            # generation observation (đúng chỗ Langfuse dùng để tính cost),
            # root span chỉ giữ thông tin định danh để nối trace với log.
            update_span(
                langfuse_client,
                version=prompt.version,
                metadata={
                    "doc_count": len(docs),
                    "query_preview": query_preview,
                    "prompt_name": prompt.name,
                    "prompt_label": prompt.label,
                    "prompt_version": prompt.version,
                    "prompt_source": prompt.source,
                    "prompt_fetch_error": prompt.fetch_error or "",
                },
            )

        # Ghi nhận Prometheus/Metrics
        metrics.record_request(
            latency_ms=latency_ms,
            ttft_ms=response.ttft_ms,
            cost_usd=cost_usd,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            quality_score=quality_score,
        )

        return AgentResult(
            answer=response.text,
            latency_ms=latency_ms,
            ttft_ms=response.ttft_ms,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            cost_usd=cost_usd,
            quality_score=quality_score,
        )

    def _estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        input_cost = (tokens_in / 1_000_000) * self.INPUT_COST_PER_MTOK
        output_cost = (tokens_out / 1_000_000) * self.OUTPUT_COST_PER_MTOK
        return round(input_cost + output_cost, 6)

    def _heuristic_quality(self, question: str, answer: str, docs: list[str]) -> float:
        score = 0.5
        if docs:
            score += 0.2
        if len(answer) > 40:
            score += 0.1
        if question.lower().split()[0:1] and any(token in answer.lower() for token in question.lower().split()[:3]):
            score += 0.1
        if "[REDACTED" in answer:
            score -= 0.2
        return round(max(0.0, min(1.0, score)), 2)