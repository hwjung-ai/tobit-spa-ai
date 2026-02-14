from __future__ import annotations

import json
import logging

from core.config import AppSettings
from pydantic import BaseModel, ValidationError
from schemas import AnswerBlock, MarkdownBlock

from app.llm.client import get_llm_client, is_llm_available

# Import real executors
from app.modules.ops.services.executors import (
    run_config,
    run_graph,
    run_hist,
    run_metric,
)
from app.shared import config_loader


class OpsAllPlan(BaseModel):
    run_config: bool = True  # Always run config by default
    run_metric: bool = False
    run_hist: bool = False
    run_graph: bool = False
    time_hint: str | None = None
    metric_hint: str | None = None
    ci_hint: str | None = None


class OpsAllRunner:
    """OPS ALL mode runner - executes config, metric, hist, and graph executors in sequence"""
    EXECUTOR_ORDER = ("config", "metric", "hist", "graph")
    EXECUTOR_MAP = {
        "config": run_config,
        "metric": run_metric,
        "hist": run_hist,
        "graph": run_graph,
    }

    def __init__(self, settings: AppSettings):
        if not is_llm_available(settings):
            raise ValueError("LLM provider is not configured for OPS ALL mode")
        self.settings = settings
        self._llm = get_llm_client()

    def run(self, question: str) -> tuple[list[AnswerBlock], list[str], str | None]:
        try:
            plan = self._plan(question)
        except Exception as exc:
            logging.exception("OPS ALL plan failed")
            block = MarkdownBlock(
                type="markdown",
                title="OPS ALL plan error",
                content="프롬프트 로드 실패 또는 LLM 계획 수립 오류로 실행하지 못했습니다.",
            )
            return [block], ["prompt"], str(exc)
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
                result = executor(question_with_hints)
                # Handle ExecutorResult or tuple returns
                if hasattr(result, "blocks") and hasattr(result, "used_tools"):
                    # ExecutorResult object
                    blocks = result.blocks
                    tools = result.used_tools
                elif isinstance(result, tuple):
                    # Legacy tuple return
                    blocks, tools = result
                else:
                    raise ValueError(
                        f"Executor {name} returned unexpected type: {type(result)}"
                    )

                executor_blocks[name] = blocks
                for tool in tools:
                    if tool not in used_tools:
                        used_tools.append(tool)
            except (
                Exception
            ) as exc:  # pragma: no cover (OPS ALL plan may hit missing data)
                logging.exception("OPS ALL executor %s failed", name)
                errors.append(f"{name}: {exc}")

        if not executor_blocks:
            raise RuntimeError("OPS ALL plan skipped all executors")

        aggregated_blocks = [
            block
            for order in self.EXECUTOR_ORDER
            for block in executor_blocks.get(order, [])
        ]
        final_summary = self._build_final_summary(question, plan, aggregated_blocks)
        ordered_blocks = [final_summary]
        for name in self.EXECUTOR_ORDER:
            ordered_blocks.extend(executor_blocks.get(name, []))

        error_info = "; ".join(errors) if errors else None
        return ordered_blocks, used_tools, error_info

    def _plan(self, question: str) -> OpsAllPlan:
        templates = self._load_prompt_templates()
        system_prompt = templates.get("plan_system")
        user_template = templates.get("plan_user")
        if not system_prompt or not user_template:
            raise RuntimeError("OPS ALL plan prompt templates are missing")
        prompt = user_template.replace("{question}", question)
        response = self._call_llm(prompt, system_prompt)
        try:
            payload = json.loads(response)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"OPS ALL plan JSON decode failed: {exc}")
        try:
            return OpsAllPlan(**payload)
        except ValidationError as exc:
            raise RuntimeError(f"OPS ALL plan validation failed: {exc}")

    def _ensure_default_plan(self, plan: OpsAllPlan) -> OpsAllPlan:
        if not any((plan.run_config, plan.run_metric, plan.run_hist, plan.run_graph)):
            return OpsAllPlan(run_config=True, run_metric=True, run_hist=True)
        return plan

    def _apply_hints(self, question: str, plan: OpsAllPlan) -> str:
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

    def _build_final_summary(
        self, question: str, plan: OpsAllPlan, blocks: list[AnswerBlock]
    ) -> MarkdownBlock:
        descriptions = self._describe_blocks(blocks)
        try:
            templates = self._load_prompt_templates()
            system_prompt = templates.get("summary_system")
            user_template = templates.get("summary_user")
            if not system_prompt or not user_template:
                raise RuntimeError("OPS ALL summary prompt templates are missing")
            prompt = (
                user_template.replace("{question}", question)
                .replace("{plan}", str(plan.model_dump()))
                .replace("{evidence}", descriptions)
            )
            content = self._call_llm(prompt, system_prompt)
            content = content.strip()
            if not content:
                raise RuntimeError("OPS ALL summary returned empty content")
        except Exception:
            logging.exception("OPS ALL summary call failed")
            content = f"OPS ALL summary unavailable; executed {', '.join([name for name in self.EXECUTOR_ORDER if getattr(plan, f'run_{name}')])}."
        return MarkdownBlock(type="markdown", title="final summary", content=content)

    def _describe_blocks(self, blocks: list[AnswerBlock]) -> str:
        if not blocks:
            return "None"
        lines = []
        for block in blocks:
            # Handle both dict and object blocks
            if isinstance(block, dict):
                block_type = block.get("type", "unknown")
                title = block.get("title", "") or block_type
            else:
                block_type = getattr(block, "type", "unknown")
                title = getattr(block, "title", "") or block_type
            lines.append(f"- {block_type}: {title}")
        return "\n".join(lines)

    def _call_llm(self, prompt: str, system_prompt: str) -> str:
        input_data = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        try:
            # Responses API
            response = self._llm.create_response(
                input=input_data, model=self.settings.chat_model, temperature=0.1
            )
        except Exception as exc:
            if self._is_temperature_not_supported_error(exc):
                logging.warning(
                    "OPS ALL model %s does not allow overriding temperature; using default",
                    self.settings.chat_model,
                )
                response = self._llm.create_response(
                    input=input_data, model=self.settings.chat_model
                )
            else:
                raise

        content = self._llm.get_output_text(response)
        if not content:
            raise RuntimeError("OPS ALL LLM returned empty content")
        return content.strip()

    def _load_prompt_templates(self) -> dict[str, str]:
        from app.modules.asset_registry.loader import load_prompt_asset

        # Try to load from asset registry first with ops scope
        prompt_data = load_prompt_asset(scope="ops", engine="ops_all", name="ops_all")
        if not prompt_data:
            # Fallback to config file
            prompt_data = config_loader.load_yaml("prompts/ops/ops_all.yaml")

        if not prompt_data or "templates" not in prompt_data:
            raise RuntimeError("OPS ALL prompt templates not found")
        templates = prompt_data.get("templates") or prompt_data.get("output_contract", {}).get("templates") or {}
        if not isinstance(templates, dict):
            raise RuntimeError("OPS ALL prompt templates invalid")
        return templates

    def _is_temperature_not_supported_error(self, exc: Exception) -> bool:
        message = str(exc)
        # Handle both "Unsupported value" and "Unsupported parameter" error messages
        return (
            "Unsupported value" in message or "Unsupported parameter" in message
        ) and "temperature" in message
