from __future__ import annotations

from app.modules.simulation.schemas import SimulationTemplate


def get_templates() -> list[SimulationTemplate]:
    return [
        SimulationTemplate(
            id="traffic-up-20",
            name="Traffic +20%",
            description="Estimate impact when request traffic increases by 20%",
            scenario_type="what_if",
            default_strategy="rule",
            assumptions={"traffic_change_pct": 20, "cpu_change_pct": 10, "memory_change_pct": 5},
            question_example="트래픽이 20% 증가하면 서비스 지표가 어떻게 변하나?",
        ),
        SimulationTemplate(
            id="cpu-pressure",
            name="CPU Pressure",
            description="Estimate degradation under high CPU pressure",
            scenario_type="stress_test",
            default_strategy="stat",
            assumptions={"cpu_change_pct": 35, "traffic_change_pct": 10, "memory_change_pct": 8},
            question_example="CPU 부담이 커질 때 응답시간과 에러율 영향은?",
        ),
        SimulationTemplate(
            id="capacity-scale",
            name="Capacity Scale",
            description="Estimate KPI change for scale planning",
            scenario_type="capacity",
            default_strategy="ml",
            assumptions={"traffic_change_pct": 45, "cpu_change_pct": 15, "memory_change_pct": 12},
            question_example="향후 45% 트래픽 증가를 버티려면 어느 KPI가 임계에 닿나?",
        ),
        SimulationTemplate(
            id="peak-storm-dl",
            name="Peak Storm (DL)",
            description="Deep sequence-style estimation for burst traffic scenario",
            scenario_type="stress_test",
            default_strategy="dl",
            assumptions={"traffic_change_pct": 80, "cpu_change_pct": 30, "memory_change_pct": 20},
            question_example="피크 트래픽 급증 시 병목 전파를 딥러닝 전략으로 추정해줘",
        ),
    ]
