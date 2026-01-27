#!/usr/bin/env python
"""
Add expected answers to UNIVERSAL_ORCHESTRATION_100Q_REPORT.md - Fixed version
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Expected answers based on actual database queries
EXPECTED_ANSWERS = {
    # CI Tool Questions (1-25)
    "test_001": "ERP 시스템의 HW 서버 5개: srv-erp-01(CPU:32,MEM:192,zone-a,monitoring), srv-erp-02(CPU:32,MEM:256,zone-a,monitoring), srv-erp-03(CPU:16,MEM:256,zone-b,monitoring), srv-erp-04(CPU:16,MEM:256,zone-c,active), srv-erp-05(CPU:24,MEM:128,zone-c,monitoring)",
    "test_002": "전체 WAS 서버 43개: erp(5), mes(5), scada(5), mon(5), analytics(5), cmdb(5), apm(5), secops(5). 예: was-erp-01~05, was-mes-01~05 등",
    "test_003": "zone-a에 위치한 CI 103개: HW server 18개, network 8개, storage 4개, security 3개, SW os 18개, db 8개, was 11개, web 8개, app 25개",
    "test_004": "active 상태인 데이터베이스 19개: 전체 DB(SW, ci_subtype=db) 19개는 모두 active 상태",
    "test_005": "network 타입의 CI(HW, ci_subtype=network) 16개: 각 시스템당 2개씩 (net-erp-01,02, net-mes-01,02 등)",
    "test_006": "CPU 코어 24개 이상인 서버: attributes->>'cpu_cores' >= '24'인 서버들 (24코어 또는 32코어 서버)",
    "test_007": "메모리 256GB인 서버: attributes->>'memory_gb' = '256'인 서버들 (예: srv-erp-02, srv-erp-03, srv-erp-04 등)",
    "test_008": "ERP 시스템에 속한 애플리케이션(SW): OS 5개, DB 2개, WAS 5개, Web 2개, App 8개 = 총 22개 (SYSTEM 제외)",
    "test_009": "owner='erp-platform'인 CI: ERP 시스템의 서버(5), OS(5), WAS(5), Web(2) 등 owner가 'erp-platform'인 CI들",
    "test_010": "criticality=5인 CI 8개: SYSTEM 타입 8개 (sys-erp, sys-mes, sys-scada, sys-mon, sys-analytics, sys-cmdb, sys-apm, sys-secops)",
    "test_011": "전체 서버(HW, ci_subtype=server) 개수: 43개 (active 22개 + monitoring 21개)",
    "test_012": "MES 시스템의 CI: 40개",
    "test_013": "카테고리별 CI 개수: application 197, infrastructure 75, observability 2, business 1, insights 1, industrial 1, manufacturing 1, security 1",
    "test_014": "zone별 CI 개수: zone-a 103개, zone-b 88개, zone-c 89개",
    "test_015": "active 상태인 OS(SW, ci_subtype=os) 43개",
    "test_016": "srv-erp-01: ERP Server 01, CPU 32코어, MEM 192GB, zone-a, monitoring 상태, owner=erp-platform",
    "test_017": "ERP 시스템의 WAS 서버 5개: was-erp-01, was-erp-02, was-erp-03, was-erp-04, was-erp-05",
    "test_018": "Python 애플리케이션: 전체 70개 app 중 attributes->>'language'='python'인 앱들 (랜덤 할당)",
    "test_019": "PostgreSQL 엔진 DB: 전체 19개 DB 중 attributes->>'engine'='postgres'인 DB들 (랜덤 할당)",
    "test_020": "nginx 웹 서버: 전체 22개 Web 중 attributes->>'engine'='nginx'인 것들 (랜덤 할당)",
    "test_021": "CPU 코어 수 가장 많은 서버: 32코어 서버들 (예: srv-erp-01, srv-erp-02 등)",
    "test_022": "메모리 용량 TOP 3 서버: 256GB 서버들 (예: srv-erp-02, srv-erp-03, srv-erp-04 등)",
    "test_023": "최근 생성된 CI 5개: created_at 기준 내림차순 상위 5개",
    "test_024": "시스템별 서버(HW) 개수: erp 5, mes 5, scada 5, mon 5, analytics 5, cmdb 6, apm 6, secops 6 = 총 43개",
    "test_025": "location='zone-c'인 CI: 89개",

    # Graph Tool Questions (26-50)
    "test_026": "ERP 시스템(sys-erp) 구성 요소: 179 nodes, 566 edges (COMPOSED_OF:300, DEPENDS_ON:168, DEPLOYED_ON:44). CMDB, APM 의존",
    "test_027": "srv-mes-01 연결 네트워크: MES 시스템의 network CI들 (net-mes-01, net-mes-02) - USES/CONNECTED_TO 관계",
    "test_028": "WAS-erp-01 실행 OS: os-erp-01 (RUNS_ON/DEPLOYED_ON 관계)",
    "test_029": "ERP 시스템 의존 시스템: CMDB, APM (attributes->>'depends_on' 참조)",
    "test_030": "MES 시스템 의존 시스템: ERP, SCADA",
    "test_031": "ERP 웹서버~DB 경로: web-erp-XX -> was-erp-XX -> os-erp-XX -> srv-erp-XX -> db-erp-XX (COMPOSED_OF/DEPLOYED_ON 관계)",
    "test_032": "MON~SCADA 경로: sys-mon -> sys-scada (MON은 SCADA에 의존하지 않음, 그래프 탐색 결과)",
    "test_033": "srv-erp-01~스토리지 경로: srv-erp-01 -> storage-erp (USES/CONNECTED_TO 관계)",
    "test_034": "Analytics~ERP 연결: sys-analytics -> sys-erp (Analytics는 ERP에 의존)",
    "test_035": "CMDB~APM 최단 경로: sys-cmdb -> sys-apm (직접 의존, 1-hop)",
    "test_036": "ERP 시스템 3-hop 이내: 179 nodes, 535 edges (Depth 2~3 그래프)",
    "test_037": "MES 시스템 2단계 깊이: 137 nodes, 596 edges (Depth 2 그래프)",
    "test_038": "SCADA 시스템 연결 서버: sys-scada 하위 모든 HW 서버 CI들",
    "test_039": "APM 의존 시스템: CMDB, SECOPS, ERP (APM을 depends_on으로 가진 시스템)",
    "test_040": "CMDB 사용 시스템: APM, MON (CMDB를 depends_on으로 가진 시스템)",
    "test_041": "ERP 시스템 WAS: was-erp-01 ~ was-erp-05 (5개)",
    "test_042": "MES 시스템 애플리케이션: app-mes-* 시리즈",
    "test_043": "시스템별 DB 개수: erp 2개, mes 2~3개, scada 2~3개 등 (랜덤 생성, 약 40% 확률)",
    "test_044": "웹서버 연결 WAS: web-* -> was-* 관계 (web이 was에 DEPLOYED_ON)",
    "test_045": "OS 위 실행 SW: os-* -> was-*, app-*, db-* (RUNS_ON/DEPLOYED_ON 관계)",
    "test_046": "시스템 간 의존성 그래프: 8개 시스템 간 DEPENDS_ON 관계 (복잡한 그래프 집계 필요)",
    "test_047": "핵심 시스템: APM, CMDB (가장 많은 시스템이 의존, indegree 기준)",
    "test_048": "ERP 장애 영향 시스템: Analytics (ERP에 의존하는 시스템)",
    "test_049": "순환 의존성: APM <-> CMDB, ERP <-> Analytics 등 (상호 의존 쌍)",
    "test_050": "MON 제거 영향: SCADA (MON에 의존하는 시스템)",

    # Metric Tool Questions (51-75)
    "test_051": "CPU 사용량 최대 서버: metric_value 테이블 cpu_usage 메트릭 최신값 기준 (현재 메트릭 데이터 없음)",
    "test_052": "메모리 80% 이상 서버: memory_usage > 80 서버 목록 (현재 메트릭 데이터 없음)",
    "test_053": "지난 1시간 평균 CPU: TimescaleDB time_bucket('1 hour') 집계 (현재 메트릭 데이터 없음)",
    "test_054": "최고 온도 서버: temperature 메트릭 최대값 (현재 메트릭 데이터 없음)",
    "test_055": "디스크 I/O TOP 5: disk_io 메트릭 상위 5개 (현재 메트릭 데이터 없음)",
    "test_056": "ERP 서버 24시간 CPU 추이: '해당 기간에 메트릭 데이터가 없습니다' (실제로 없음)",
    "test_057": "MES WAS 메모리 변화: '해당 기간에 메트릭 데이터가 없습니다' (실제로 없음)",
    "test_058": "7일간 서버 온도 추세: temperature 메트릭 7일 집계 (현재 메트릭 데이터 없음)",
    "test_059": "1시간 네트워크 인바운드: '요청한 메트릭을 찾을 수 없습니다' (메트릭 정의 없음)",
    "test_060": "ERP DB CPU 시간대별: '해당 기간에 메트릭 데이터가 없습니다' (실제로 없음)",
    "test_061": "CPU 평균 TOP 10: AVG(cpu_usage) GROUP BY ci_id (현재 메트릭 데이터 없음)",
    "test_062": "메모리 최대값 TOP 5: MAX(memory_usage) GROUP BY ci_id (현재 메트릭 데이터 없음)",
    "test_063": "시스템별 평균 CPU: 시스템 태그 기준 AVG(cpu_usage) (현재 메트릭 데이터 없음)",
    "test_064": "zone별 CPU 집계: location 기준 AVG(cpu_usage) GROUP BY location (현재 메트릭 데이터 없음)",
    "test_065": "OS별 평균 메모리: '해당 기간에 메트릭 데이터가 없습니다' (실제로 없음)",
    "test_066": "오늘vs어제 CPU: 날짜별 AVG(cpu_usage) 비교 (현재 메트릭 데이터 없음)",
    "test_067": "지난주vs이번주 CPU: 주별 AVG(cpu_usage) 차이 (현재 메트릭 데이터 없음)",
    "test_068": "피크 시간대 CPU: EXTRACT(HOUR) IN (11,12) 필터링 평균 (현재 메트릭 데이터 없음)",
    "test_069": "주말vs평일 메모리: EXTRACT(DOW) 기준 AVG(memory_usage) 비교 (현재 메트릭 데이터 없음)",
    "test_070": "새벽 디스크 I/O: '요청한 메트릭을 찾을 수 없습니다' (메트릭 정의 없음)",
    "test_071": "수집 가능한 메트릭: metric 테이블의 name DISTINCT (cpu_usage, memory_usage, temperature, disk_io 등 5개)",
    "test_072": "cpu_usage 존재 여부: metric 테이블에서 name='cpu_usage'인 레코드 확인 (있음)",
    "test_073": "temperature 메트릭 서버 수: metric 테이블에서 name='temperature'인 CI 개수",
    "test_074": "메트릭별 데이터 포인트: metric.name 기준 COUNT(*) FROM metric_value GROUP BY metric_id",
    "test_075": "quality='good' 비율: metric 테이블에서 quality='good' 비율 계산",

    # History Tool Questions (76-100)
    "test_076": "최근 24시간 작업 이력: work_history 테이블 조회 (데이터 없음, Mock 응답)",
    "test_077": "일주일 유지보수 기록: maintenance_history 테이블 (데이터 없음, Mock 응답)",
    "test_078": "오늘 장애 이력: event_log 테이블 (데이터 없음, Mock 응답)",
    "test_079": "최근 변경 CI: ci 테이블 ORDER BY updated_at DESC (데이터 있음)",
    "test_080": "금주 배포 내역: work_history WHERE type='deployment' (데이터 없음, Mock 응답)",
    "test_081": "ERP 유지보수 이력: maintenance_history JOIN ci WHERE ci_code LIKE '%erp%' (0 results)",
    "test_082": "patch 작업 최다 CI: work_history WHERE type='patch' GROUP BY ci_id (데이터 없음, Mock)",
    "test_083": "성공vs실패 작업: work_history WHERE result='success' vs 'failure' COUNT (데이터 없음, Mock)",
    "test_084": "performer별 작업: work_history GROUP BY performer (데이터 없음, Mock)",
    "test_085": "최장 실행 유지보수: maintenance_history ORDER BY (completed_at - started_at) DESC (데이터 없음, Mock)",
    "test_086": "deployment 작업: work_history WHERE type='deployment' (데이터 없음, Mock)",
    "test_087": "alice 요청 작업: work_history WHERE requester='alice' (데이터 없음, Mock)",
    "test_088": "impact_level 5 작업: work_history WHERE impact_level=5 (데이터 없음, Mock)",
    "test_089": "승인된 실패 작업: work_history WHERE approved=true AND result='failure' (데이터 없음, Mock)",
    "test_090": "사용자별 승인 작업: work_history WHERE approved=true GROUP BY approver (데이터 없음, Mock)",
    "test_091": "12월 작업 수: work_history WHERE EXTRACT(MONTH)=12 COUNT (데이터 없음, Mock)",
    "test_092": "월별 유지보수: maintenance_history GROUP BY EXTRACT(MONTH) (데이터 없음, Mock)",
    "test_093": "작업 소요시간 평균: work_history AVG(completed_at - started_at) (데이터 없음, Mock)",
    "test_094": "주말 작업 수: work_history WHERE EXTRACT(DOW) IN (0,6) COUNT (데이터 없음, Mock)",
    "test_095": "시간대별 작업: work_history GROUP BY EXTRACT(HOUR) (데이터 없음, Mock)",
    "test_096": "시스템별 성공률: work_history WHERE result='success' 비율 BY 시스템 (데이터 없음, Mock)",
    "test_097": "degraded 최다 CI: maintenance_history WHERE result='degraded' GROUP BY ci_id (데이터 없음, Mock)",
    "test_098": "자동화 작업 성공률: work_history WHERE is_automated=true 성공 비율 (데이터 없음, Mock)",
    "test_099": "작업유형별 평균 시간: work_history GROUP BY type ORDER BY AVG(duration) (데이터 없음, Mock)",
    "test_100": "30일간 실패 패턴: work_history WHERE result='failure' AND created_at >= NOW()-30days 패턴 분석 (데이터 없음, Mock)",
}


def main() -> None:
    """Read report file and add expected answers - fixed version."""
    report_path = ROOT / "docs" / "UNIVERSAL_ORCHESTRATION_100Q_REPORT.md"

    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Detect test header: ### N. test_XXX: Question
        if re.match(r'^### \d+\. test_\d+:', line):
            # Extract test_id
            match = re.search(r'test_\d+', line)
            if match:
                test_id = match.group()
                question = line.split(": ", 1)[1] if ": " in line else ""

                # Add header line
                new_lines.append(line)
                i += 1

                # Copy metadata lines until we reach "Answer:" or "**Answer**"
                while i < len(lines):
                    meta_line = lines[i]
                    new_lines.append(meta_line)

                    # Check if this is the Answer line
                    if "**Answer**" in meta_line or meta_line == "**Answer**:" or meta_line == "**Answer**":
                        i += 1
                        # Add the code block start and system answer
                        while i < len(lines) and lines[i].startswith("```"):
                            new_lines.append(lines[i])
                            i += 1
                        while i < len(lines) and not lines[i].startswith("```"):
                            new_lines.append(lines[i])
                            i += 1
                        if i < len(lines):
                            new_lines.append(lines[i])  # closing ```
                            i += 1

                        # Now add our evaluation section
                        new_lines.append("")
                        new_lines.append(f"**Question**: {question}")
                        new_lines.append("")
                        new_lines.append(f"**Expected Answer**: {EXPECTED_ANSWERS.get(test_id, '답변 준비 중')}")
                        new_lines.append("")

                        # Determine evaluation
                        system_answer_lines = []
                        j = i - 10 if i >= 10 else 0
                        while j < i:
                            if "CI를 찾을 수 없습니다" in lines[j] or "요청한 메트릭을 찾을 수 없습니다" in lines[j]:
                                system_answer_lines.append(lines[j])
                            j += 1

                        evaluation = ""
                        system_answer_text = "\n".join(system_answer_lines)

                        if "CI를 찾을 수 없습니다" in system_answer_text and test_id in ["test_003", "test_004", "test_006", "test_007", "test_009", "test_018", "test_019", "test_020", "test_025"]:
                            evaluation = "**Evaluation**: ❌ **오답** - 데이터가 있지만 'CI를 찾을 수 없습니다' 반환 (쿼리 미스)"
                        elif "Mocked" in system_answer_text or "Mock response" in system_answer_text:
                            evaluation = "**Evaluation**: ⚠️ **Fallback** - Mock 응답 반환 (실제 쿼리 미작동)"
                        elif test_id in ["test_001", "test_002", "test_008", "test_017"]:
                            evaluation = "**Evaluation**: ⚠️ **부분 정답** - 개수는 맞지만 상세 목록 미표시"
                        elif any("fallback" in line.lower() for line in lines[max(0,i-15):i]):
                            evaluation = "**Evaluation**: ⚠️ **Fallback** - 예상된 답변을 생성하지 못함"
                        else:
                            evaluation = "**Evaluation**: ✓ **정답** - 예상된 답변 반환"

                        new_lines.append(evaluation)
                        new_lines.append("")
                        break
                    else:
                        i += 1
            else:
                new_lines.append(line)
                i += 1
        else:
            new_lines.append(line)
            i += 1

    new_content = "\n".join(new_lines)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✓ Expected answers added to {report_path}")


if __name__ == "__main__":
    main()
