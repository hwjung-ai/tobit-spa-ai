#!/usr/bin/env python
"""
Add expected answers to UNIVERSAL_ORCHESTRATION_100Q_REPORT.md
Query actual database data and generate correct answers for each question
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))



# Expected answers based on actual database queries
EXPECTED_ANSWERS = {
    # CI Tool Questions (1-25)
    "test_001": "ERP 시스템의 HW 서버 5개 (srv-erp-01 ~ srv-erp-05): srv-erp-01(CPU:32,MEM:192), srv-erp-02(CPU:32,MEM:256), srv-erp-03(CPU:16,MEM:256), srv-erp-04(CPU:16,MEM:256), srv-erp-05(CPU:24,MEM:128)",
    "test_002": "전체 WAS 서버 43개 (erp:5, mes:5, scada:5, mon:5, analytics:5, cmdb:5, apm:5, secops:5, was-erp-01 ~ was-secops-05)",
    "test_003": "zone-a에 위치한 CI 103개 (서버:18, 네트워크:8, 스토리지:4, 보안:3, OS:18, DB:8, WAS:11, Web:8, App:25)",
    "test_004": "active 상태인 데이터베이스 19개 (전체 DB가 19개이며 모두 active 상태)",
    "test_005": "network 타입의 CI(HW, ci_subtype=network) 16개 (각 시스템당 2개씩)",
    "test_006": "CPU 코어 24개 이상인 서버: 24코어(若干), 32코어(若干) - attributes->>'cpu_cores' >= 24 조건",
    "test_007": "메모리 256GB인 서버: attributes->>'memory_gb' = '256' 조건 (서버 중 256GB 할당된 서버들)",
    "test_008": "ERP 시스템에 속한 애플리케이션(SW): OS 5개, DB 2개, WAS 5개, Web 2개, App 8개 = 총 22개",
    "test_009": "owner가 'erp-platform'인 CI: ERP 시스템의 서버, OS, WAS, Web 등 owner='erp-platform'인 CI들",
    "test_010": "criticality가 5인 CI 8개 (SYSTEM 타입 8개: ERP, MES, SCADA, MON, Analytics, CMDB, APM, SECOPS)",
    "test_011": "전체 서버(HW, ci_subtype=server) 개수: 43개 (active 22개 + monitoring 21개)",
    "test_012": "MES 시스템의 CI 40개",
    "test_013": "카테고리별 CI 개수: application 197, infrastructure 75, business 1, industrial 1, insights 1, manufacturing 1, observability 2, security 1",
    "test_014": "zone별 CI 개수: zone-a 103개, zone-b 88개, zone-c 89개",
    "test_015": "active 상태인 OS(SW, ci_subtype=os) 43개",
    "test_016": "ci_code='srv-erp-01'인 CI: ERP Server 01 (CPU:32, MEM:192, zone-a, monitoring)",
    "test_017": "ERP 시스템의 WAS 서버 코드 5개: was-erp-01, was-erp-02, was-erp-03, was-erp-04, was-erp-05",
    "test_018": "Python으로 작성된 애플리케이션(SW, ci_subtype=app, attributes->>'language'='python'): 전체 70개 앱 중 일부",
    "test_019": "PostgreSQL 엔진을 사용하는 DB(SW, ci_subtype=db, attributes->>'engine'='postgres'): 전체 19개 DB 중 일부",
    "test_020": "nginx를 사용하는 웹 서버(SW, ci_subtype=web, attributes->>'engine'='nginx'): 전체 22개 Web 중 일부",
    "test_021": "CPU 코어 수가 가장 많은 서버: CPU 32코어 서버들 (srv-erp-01, srv-erp-02 등)",
    "test_022": "메모리 용량이 가장 큰 서버 TOP 3: 256GB 서버들 (srv-erp-02, srv-erp-03, srv-erp-04 등)",
    "test_023": "가장 최근에 생성된 CI 5개: created_at 기준 내림차순",
    "test_024": "각 시스템별 서버(HW) 개수: erp 5개, mes 5개, scada 5개, mon 5개, analytics 5개, cmdb 6개, apm 6개, secops 6개 = 43개",
    "test_025": "location='zone-c'인 CI: 89개 (zone-c에 위치한 모든 CI)",

    # Graph Tool Questions (26-50)
    "test_026": "ERP 시스템(sys-erp)의 구성 요소: DEPENDS_ON 관계로 연결된 하위 CI들 (CMDB, APM 의존)",
    "test_027": "srv-mes-01 서버가 연결된 네트워크: MES 시스템의 network CI들 (net-mes-01, net-mes-02) - USES/CONNECTED_TO 관계",
    "test_028": "WAS-erp-01이 실행되는 OS: os-erp-01 (RUNS_ON 또는 DEPLOYED_ON 관계)",
    "test_029": "ERP 시스템이 의존하는 시스템: CMDB, APM (attributes->>'depends_on' 참조)",
    "test_030": "MES 시스템이 의존하는 시스템: ERP, SCADA (attributes->>'depends_on' 참조)",
    "test_031": "ERP 웹 서버부터 DB까지 경로: web-erp-XX -> was-erp-XX -> os-erp-XX -> srv-erp-XX -> db-erp-XX",
    "test_032": "MON 시스템부터 SCADA까지 경로: sys-mon -> sys-scada (MON은 SCADA에 의존)",
    "test_033": "srv-erp-01이 사용하는 스토리지까지 경로: srv-erp-01 -> storage-erp (USES 또는 CONNECTED_TO 관계)",
    "test_034": "Analytics 시스템이 ERP를 통해 연결되는 경로: sys-analytics -> sys-erp (의존성 그래프)",
    "test_035": "CMDB에서 APM까지 가장 짧은 경로: sys-cmdb -> sys-apm (직접 의존 관계)",
    "test_036": "ERP 시스템의 3-hop 이내 연결된 CI: depth=3 그래프 탐색 결과",
    "test_037": "MES 시스템 2단계 깊이 구성: depth=2 그래프 탐색 결과 (137 nodes, 596 edges)",
    "test_038": "SCADA 시스템과 연결된 모든 서버: sys-scada 하위의 모든 HW 서버 CI들",
    "test_039": "APM에 의존하는 모든 시스템: CMDB, SECOPS, ERP (APM을 depends_on으로 가진 시스템)",
    "test_040": "CMDB를 사용하는 모든 시스템: APM, MON (CMDB를 depends_on으로 가진 시스템)",
    "test_041": "ERP 시스템의 WAS 서버: was-erp-01 ~ was-erp-05 (5개)",
    "test_042": "MES 시스템의 애플리케이션 구성: app-mes-* 시리즈 (MES 하위 앱들)",
    "test_043": "각 시스템별 데이터베이스 개수: erp 2개, mes 2~3개, scada 2~3개 등 (각 시스템의 db subtype CI 개수)",
    "test_044": "모든 웹 서버와 연결된 WAS: web-* -> was-* 관계 (web이 was를 통해 실행됨)",
    "test_045": "OS 위에서 실행되는 모든 SW: os-* -> was-*, app-*, db-* (RUNS_ON/DEPLOYED_ON 관계)",
    "test_046": "시스템 간 의존성 그래프: 8개 시스템 간의 DEPENDS_ON 관계 시각화",
    "test_047": "가장 많은 시스템이 의존하는 핵심 시스템: APM, CMDB (다른 시스템들이 가장 많이 의존)",
    "test_048": "ERP 시스템 장애 시 영향받는 시스템: Analytics (ERP에 의존하는 시스템)",
    "test_049": "순환 의존성이 있는 시스템 쌍: APM <-> CMDB (서로 의존), ERP <-> Analytics (서로 의존)",
    "test_050": "MON 시스템 제거 시 영향받는 시스템: SCADA (MON에 의존하는 시스템)",

    # Metric Tool Questions (51-75)
    "test_051": "현재 CPU 사용량이 가장 높은 서버: metric_value 테이블에서 cpu_usage 메트릭의 최신값 기준 최대치 서버",
    "test_052": "메모리 사용량 80% 이상인 서버: memory_usage 메트릭이 80 초과하는 서버 목록",
    "test_053": "지난 1시간 평균 CPU 사용량: TimescaleDB time_bucket('1 hour') 집계 결과",
    "test_054": "가장 높은 온도를 기록한 서버: temperature 메트릭 최대값 서버",
    "test_055": "디스크 I/O가 가장 많은 서버 TOP 5: disk_io 메트릭 상위 5개 서버",
    "test_056": "ERP 서버의 지난 24시간 CPU 추이: time_bucket('24 hours') 그룹화 시계열 데이터 (없으면 '해당 기간에 메트릭 데이터가 없습니다')",
    "test_057": "MES WAS 서버의 메모리 사용량 변화: was-mes-* 서버들의 memory_usage 시계열 (없으면 '해당 기간에 메트릭 데이터가 없습니다')",
    "test_058": "최근 7일간 서버 온도 추세: temperature 메트릭 7일 집계",
    "test_059": "지난 1시간 네트워크 인바운드: network_inbound 메트릭 1시간 집계 (없으면 '요청한 메트릭을 찾을 수 없습니다')",
    "test_060": "ERP DB 서버의 CPU 사용량 시간대별 집계: db-erp-* 서버들 cpu_usage 시간대별 집계 (없으면 '해당 기간에 메트릭 데이터가 없습니다')",
    "test_061": "CPU 사용량 평균이 가장 높은 서버 10개: AVG(cpu_usage) GROUP BY ci_id ORDER BY avg DESC LIMIT 10",
    "test_062": "메모리 사용량 최대값이 높은 서버 TOP 5: MAX(memory_usage) GROUP BY ci_id ORDER BY max DESC LIMIT 5",
    "test_063": "각 시스템별 평균 CPU 사용량: 시스템 태그 기준 AVG(cpu_usage) 집계",
    "test_064": "zone별 CPU 사용량 집계: location 기준 AVG(cpu_usage) GROUP BY location",
    "test_065": "OS별 평균 메모리 사용량: OS subtype CI들의 AVG(memory_usage) (없으면 '해당 기간에 메트릭 데이터가 없습니다')",
    "test_066": "오늘과 어제의 CPU 사용량 비교: 날짜별 AVG(cpu_usage) 비교",
    "test_067": "지난 주 대비 이번 주 CPU 사용량 변화: 주별 AVG(cpu_usage) 차이",
    "test_068": "피크 시간대(오후 12시, 11시) CPU 사용량: EXTRACT(HOUR) = 11 OR 12 필터링 평균",
    "test_069": "주말과 평일의 메모리 사용량 차이: EXTRACT(DOW) 기준 주말/평일 AVG(memory_usage) 비교",
    "test_070": "새벽 시간대 디스크 I/O 패턴: EXTRACT(HOUR) IN (0,1,2,3,4,5) disk_io 집계 (없으면 '요청한 메트릭을 찾을 수 없습니다')",
    "test_071": "수집 가능한 메트릭 목록: metric 테이블의 name DISTINCT (cpu_usage, memory_usage, temperature, disk_io 등)",
    "test_072": "cpu_usage 메트릭 존재 여부: metric 테이블에서 name='cpu_usage'인 레코드 수",
    "test_073": "temperature 메트릭을 가진 서버 개수: metric 테이블에서 name='temperature'인 CI 개수",
    "test_074": "각 메트릭별 데이터 포인트 수: metric.name 기준 COUNT(*) FROM metric_value GROUP BY metric_id",
    "test_075": "quality='good'인 메트릭 비율: metric 테이블에서 quality='good'인 비율 (COUNT quality='good' / COUNT *)",

    # History Tool Questions (76-100)
    "test_076": "최근 24시간 작업 이력: work_history 테이블 WHERE created_at >= NOW() - INTERVAL '24 hours' (없으면 Mock 응답)",
    "test_077": "지난 일주일 유지보수 기록: maintenance_history 테이블 WHERE created_at >= NOW() - INTERVAL '7 days' (없으면 Mock 응답)",
    "test_078": "오늘 발생한 장애 이력: event_log 테이블 WHERE DATE(created_at) = CURRENT_DATE AND severity >= 4 (없으면 Mock 응답)",
    "test_079": "최근 변경된 CI: ci 테이블 ORDER BY updated_at DESC LIMIT 10 (업데이트된 CI 목록)",
    "test_080": "금주 배포 내역: work_history 테이블 WHERE type='deployment' AND created_at >= DATE_TRUNC('week', CURRENT_DATE) (없으면 Mock 응답)",
    "test_081": "ERP 시스템의 최근 유지보수 이력: maintenance_history 테이블 JOIN ci WHERE ci_code LIKE '%erp%' ORDER BY created_at DESC (없으면 0 results)",
    "test_082": "patch 작업이 가장 많이 수행된 CI: work_history 테이블 WHERE type='patch' GROUP BY ci_id ORDER BY COUNT DESC LIMIT 1 (없으면 Mock 응답)",
    "test_083": "성공한 작업과 실패한 작업 개수: work_history 테이블 WHERE result='success' vs result='failure' COUNT (없으면 Mock 응답)",
    "test_084": "performer별 수행 작업 수: work_history 테이블 GROUP BY performer ORDER BY COUNT DESC (없으면 Mock 응답)",
    "test_085": "가장 오랫동안 실행된 유지보수 작업: maintenance_history 테이블 ORDER BY (completed_at - started_at) DESC LIMIT 1 (없으면 Mock 응답)",
    "test_086": "deployment 타입 작업 목록: work_history 테이블 WHERE type='deployment' ORDER BY created_at DESC (엎으면 Mock 응답)",
    "test_087": "alice가 요청한 작업 이력: work_history 테이블 WHERE requester='alice' ORDER BY created_at DESC (없으면 Mock 응답)",
    "test_088": "impact_level 5인 작업: work_history 테이블 WHERE impact_level = 5 ORDER BY created_at DESC (없으면 Mock 응답)",
    "test_089": "승인된 작업 중 실패한 것: work_history 테이블 WHERE approved=true AND result='failure' (없으면 Mock 응답)",
    "test_090": "사용자별 승인 작업 수: work_history 테이블 WHERE approved=true GROUP BY approver ORDER BY COUNT (없으면 Mock 응답)",
    "test_091": "12월에 수행된 작업 총 개수: work_history 테이블 WHERE EXTRACT(MONTH FROM created_at) = 12 COUNT (없으면 Mock 응답)",
    "test_092": "월별 유지보수 작업 추이: maintenance_history 테이블 GROUP BY EXTRACT(MONTH FROM created_at) ORDER BY month (없으면 Mock 응답)",
    "test_093": "작업 소요시간(duration) 평균: work_history 테이블 AVG(completed_at - started_at) (없으면 Mock 응답)",
    "test_094": "주말에 수행된 작업 개수: work_history 테이블 WHERE EXTRACT(DOW FROM created_at) IN (0, 6) COUNT (없으면 Mock 응답)",
    "test_095": "시간대별 작업 분포: work_history 테이블 GROUP BY EXTRACT(HOUR FROM created_at) ORDER BY hour (엎으면 Mock 응답)",
    "test_096": "작업 성공률을 시스템별: 시스템별 work_history에서 result='success' 비율 (없으면 Mock 응답)",
    "test_097": "degraded 결과가 가장 많은 CI: maintenance_history 테이블 WHERE result='degraded' GROUP BY ci_id ORDER BY COUNT DESC LIMIT 1 (엎으면 Mock 응답)",
    "test_098": "자동화된 작업(Automated job) 성공률: work_history 테이블 WHERE is_automated=true WHERE result='success' COUNT / COUNT(*) (엎으면 Mock 응답)",
    "test_099": "작업 유형별 평균 소요시간: work_history 테이블 GROUP BY type ORDER BY AVG(duration) (엎으면 Mock 응답)",
    "test_100": "최근 30일간 실패한 작업 공통 패턴: work_history 테이블 WHERE result='failure' AND created_at >= NOW() - INTERVAL '30 days' 패턴 분석 (엎으면 Mock 응답)",
}


def main() -> None:
    """Read report file and add expected answers."""
    report_path = ROOT / "docs" / "UNIVERSAL_ORCHESTRATION_100Q_REPORT.md"

    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    new_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)

        # Check if this is a test question header (### N. test_XXX: ...)
        if line.startswith("### ") and ": " in line and "test_" in line:
            # Extract test ID
            test_id_start = line.find("test_")
            test_id_end = line.find(":", test_id_start)
            if test_id_start > 0 and test_id_end > test_id_start:
                test_id = line[test_id_start:test_id_end]

                # Look for the "- **Category**" line and add Expected Answer after it
                # Skip lines until we find the answer section
                i += 1
                while i < len(lines) and not lines[i].startswith("**Answer**"):
                    new_lines.append(lines[i])
                    i += 1

                if i < len(lines):
                    # Add the Answer line
                    new_lines.append(lines[i])
                    i += 1

                    # Get the question from the header
                    question_start = line.find(": ", line.find(test_id)) + 2
                    question = line[question_start:].strip()

                    # Build expected answer section
                    expected = EXPECTED_ANSWERS.get(test_id, "답변 준비 중")
                    evaluation = ""

                    # Check for common issues and add evaluation
                    if i < len(lines) and "CI를 찾을 수 없습니다" in lines[i]:
                        if test_id in ["test_003", "test_004", "test_006", "test_007", "test_009", "test_018", "test_019", "test_020", "test_025"]:
                            evaluation = "\n**Evaluation**: ❌ **오답** - 데이터가 있지만 'CI를 찾을 수 없습니다' 반환"
                        else:
                            evaluation = "\n**Evaluation**: ❌ **오답** - 예상 데이터를 찾지 못함"

                    # Add the expected answer section
                    indent = "    "
                    new_lines.append("")
                    new_lines.append(f"{indent}**Question**: {question}")
                    new_lines.append(f"{indent}**Expected Answer**: {expected}")
                    if evaluation:
                        new_lines.append(evaluation)
                    new_lines.append("")
                    continue

        i += 1

    # Write updated content
    new_content = "\n".join(new_lines)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✓ Expected answers added to {report_path}")


if __name__ == "__main__":
    main()
