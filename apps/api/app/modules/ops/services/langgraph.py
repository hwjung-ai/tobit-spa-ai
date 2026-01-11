from __future__ import annotations

import json
import logging

from pydantic import BaseModel, ValidationError

from core.config import AppSettings
from schemas import AnswerBlock, MarkdownBlock
from .executors.graph_executor import run_graph
from .executors.hist_executor import run_hist
from .executors.metric_executor import run_metric
from app.llm.client import get_llm_client


class LangGraphPlan(BaseModel):
    run_metric: bool = False
    run_hist: bool = False
    run_graph: bool = False
    time_hint: str | None = None
    metric_hint: str | None = None
    ci_hint: str | None = None


class LangGraphAllRunner:
    EXECUTOR_ORDER = ("metric", "hist", "graph")
    EXECUTOR_MAP = {
        "metric": run_metric,
        "hist": run_hist,
        "graph": run_graph,
    }

    def __init__(self, settings: AppSettings):
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key is required for LangGraph ALL mode")
        self.settings = settings
        self._llm = get_llm_client()

    def run(self, question: str) -> tuple[list[AnswerBlock], list[str], str | None]:
        plan = self._plan(question)
        plan = self._ensure_default_plan(plan)

        executor_blocks: dict[str, list[AnswerBlock]] = {}
        used_tools: list[str] = []
        errors: list[str] = []

        question_with_hints = self._apply_hints(question, plan)
        for name in self.EXECUTOR_ORDER:
            if not getattr(plan, f"run_{name}"):
                continue
            executor = self.EXECUTOR_MAP[name]
            try:
                blocks, tools = executor(question_with_hints)
                executor_blocks[name] = blocks
                for tool in tools:
                    if tool not in used_tools:
                        used_tools.append(tool)
            except Exception as exc:  # pragma: no cover (LangGraph plan may hit missing data)
                logging.exception("LangGraph executor %s failed", name)
                errors.append(f"{name}: {exc}")

        if not executor_blocks:
            raise RuntimeError("LangGraph plan skipped all executors")

        aggregated_blocks = [block for order in self.EXECUTOR_ORDER for block in executor_blocks.get(order, [])]
        final_summary = self._build_final_summary(question, plan, aggregated_blocks)
        ordered_blocks = [final_summary]
        for name in self.EXECUTOR_ORDER:
            ordered_blocks.extend(executor_blocks.get(name, []))

        error_info = "; ".join(errors) if errors else None
        return ordered_blocks, used_tools, error_info

    def _plan(self, question: str) -> LangGraphPlan:
        prompt = (
            "You are orchestrating OPS queries. The question is:\n"
            f"{question}\n\n"
            "Return only JSON that follows this schema:\n"
            "{\n"
            '  "run_metric": bool,\n'
            '  "run_hist": bool,\n'
            '  "run_graph": bool,\n'
            '  "time_hint": str | null,\n'
            '  "metric_hint": str | null,\n'
            '  "ci_hint": str | null\n'
            "}\n\n"
            "Choose the minimum set of executors needed to answer the question.\n"
            "Hint fields help suffix the question to narrow the scope.\n"
            "If unsure prefer both metric and hist."
        )
        response = self._call_llm(prompt)
        try:
            payload = json.loads(response)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"LangGraph plan JSON decode failed: {exc}")
        try:
            return LangGraphPlan(**payload)
        except ValidationError as exc:
            raise RuntimeError(f"LangGraph plan validation failed: {exc}")

    def _ensure_default_plan(self, plan: LangGraphPlan) -> LangGraphPlan:
        if not any((plan.run_metric, plan.run_hist, plan.run_graph)):
            return LangGraphPlan(run_metric=True, run_hist=True)
        return plan

    def _apply_hints(self, question: str, plan: LangGraphPlan) -> str:
        hints: list[str] = []
        if plan.ci_hint:
            hints.append(f"[CI:{plan.ci_hint}]")
        if plan.metric_hint:
            hints.append(f"[Metric:{plan.metric_hint}]")
        if plan.time_hint:
            hints.append(f"[Time:{plan.time_hint}]")
        if hints:
            return f"{' '.join(hints)} {question}"
        return question

    def _build_final_summary(self, question: str, plan: LangGraphPlan, blocks: list[AnswerBlock]) -> MarkdownBlock:
        descriptions = self._describe_blocks(blocks)
        prompt = (
            "You are a LangGraph aggregator for OPS. Produce a final Markdown summary (5-10 lines) "
            "for the question below and cite the evidence by referencing the block titles/contexts "
            "with the word '근거'. Avoid JSON.\n\n"
            f"Question: {question}\n"
            f"Plan: {plan.model_dump()}\n"
            f"Evidence:\n{descriptions}\n\n"
            "Hint at which blocks (metric SQL, history table, graph nodes) support your answer."
        )
        try:
            content = self._call_llm(prompt)
            content = content.strip()
            if not content:
                raise RuntimeError("LangGraph summary returned empty content")
        except Exception as exc:
            logging.exception("LangGraph summary call failed")
            content = (
                f"LangGraph summary unavailable; executed {', '.join([name for name in self.EXECUTOR_ORDER if getattr(plan, f'run_{name}')])}."
            )
        return MarkdownBlock(type="markdown", title="final summary", content=content)

    def _describe_blocks(self, blocks: list[AnswerBlock]) -> str:
        if not blocks:
            return "None"
        lines = []
        for block in blocks:
            title = getattr(block, "title", "") or block.type
            lines.append(f"- {block.type}: {title}")
        return "\n".join(lines)

    def _call_llm(self, prompt: str) -> str:
        input_data = [
            {"role": "system", "content": "You are a deterministic LangGraph planner/aggregator."},
            {"role": "user", "content": prompt},
        ]

        try:
            # Responses API
            response = self._llm.create_response(
                input=input_data,
                model=self.settings.chat_model,
                temperature=0.1
            )
        except Exception as exc:
            if self._is_temperature_not_supported_error(exc):
                logging.warning(
                    "LangGraph model %s does not allow overriding temperature; using default",
                    self.settings.chat_model,
                )
                response = self._llm.create_response(
                    input=input_data,
                    model=self.settings.chat_model
                )
            else:
                raise
        
        content = self._llm.get_output_text(response)
        if not content:
            raise RuntimeError("LangGraph LLM returned empty content")
        return content.strip()

    def _is_temperature_not_supported_error(self, exc: Exception) -> bool:
        message = str(exc)
        return "Unsupported value" in message and "temperature" in message
