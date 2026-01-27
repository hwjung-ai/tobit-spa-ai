#!/usr/bin/env python
"""
Add expected answers to the 100 questions test report.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Expected answers based on actual database queries
EXPECTED_ANSWERS = {
    # CI Questions (1-25)
    "test_001": "ERP 시스템의 HW 서버 5개: srv-erp-01(CPU:32,MEM:192,zone-a,monitoring), srv-erp-02(CPU:32,MEM:256,zone-a,monitoring), srv-erp-03(CPU:16,MEM:256,zone-b,monitoring), srv-erp-04(CPU:16,MEM:256,zone-c,active), srv-erp-05(CPU:24,MEM:128,zone-c,monitoring)",
    "test_002": "전체 WAS 서버 43개: erp(5), mes(5), scada(5), mon(5), analytics(5), cmdb(5), apm(5), secops(5)",
    "test_003": "zone-a에 위치한 CI 103개: HW server 18개, network 8개, storage 4개, security 3개, SW os 18개, db 8개, was 11개, web 8개, app 25개",
    "test_004": "active 상태인 데이터베이스 19개 (전체 DB가 모두 active 상태)",
    "test_005": "network 타입의 CI(HW, ci_subtype=network) 16개: 각 시스템당 2개씩",
    "test_006": "CPU 코어 24개 이상인 서버: attributes->>'cpu_cores' >= '24'인 서버들",
    "test_007": "메모리 256GB인 서버: attributes->>'memory_gb' = '256'인 서버들",
    "test_008": "ERP 시스템에 속한 애플리케이션(SW): OS 5개, DB 2개, WAS 5개, Web 2개, App 8개 = 총 22개",
    "test_009": "owner='erp-platform'인 CI: ERP 시스템의 서버, OS, WAS, Web 등 owner가 'erp-platform'인 CI들",
    "test_010": "criticality=5인 CI 8개: SYSTEM 타입 8개 (sys-erp, sys-mes, sys-scada, sys-mon, sys-analytics, sys-cmdb, sys-apm, sys-secops)",
    "test_011": "전체 서버(HW, ci_subtype=server) 개수: 43개 (active 22개 + monitoring 21개)",
    "test_012": "MES 시스템의 CI: 40개",
    "test_013": "카테고리별 CI 개수: application 197, infrastructure 75, observability 2, business/insights/industrial/manufacturing/security 각 1개",
    "test_014": "zone별 CI 개수: zone-a 103개, zone-b 88개, zone-c 89개",
    "test_015": "active 상태인 OS(SW, ci_subtype=os) 43개",
    "test_016": "srv-erp-01: ERP Server 01, CPU 32코어, MEM 192GB, zone-a, monitoring 상태, owner=erp-platform",
    "test_017": "ERP 시스템의 WAS 서버 5개: was-erp-01, was-erp-02, was-erp-03, was-erp-04, was-erp-05",
    "test_018": "Python 애플리케이션: 전체 70개 app 중 attributes->>'language'='python'인 앱들",
    "test_019": "PostgreSQL 엔진 DB: 전체 19개 DB 중 attributes->>'engine'='postgres'인 DB들",
    "test_020": "nginx 웹 서버: 전체 22개 Web 중 attributes->>'engine'='nginx'인 것들",
    "test_021": "CPU 코어 수 가장 많은 서버: 32코어 서버들 (예: srv-erp-01, srv-erp-02 등)",
    "test_022": "메모리 용량 TOP 3 서버: 256GB 서버들",
    "test_023": "최근 생성된 CI 5개: created_at 기준 내림차순 상위 5개",
    "test_024": "시스템별 서버(HW) 개수: erp 5, mes 5, scada 5, mon 5, analytics 5, cmdb 6, apm 6, secops 6 = 총 43개",
    "test_025": "location='zone-c'인 CI: 89개",
    # Graph Questions (26-50)
    "test_026": "ERP 시스템(sys-erp) 구성 요소: 179 nodes, 566 edges (COMPOSED_OF:300, DEPENDS_ON:168, DEPLOYED_ON:44)",
    "test_027": "srv-mes-01 연결 네트워크: net-mes-01, net-mes-02 (USES/CONNECTED_TO 관계)",
    "test_028": "WAS-erp-01 실행 OS: os-erp-01 (RUNS_ON/DEPLOYED_ON 관계)",
    "test_029": "ERP 시스템 의존 시스템: CMDB, APM (depends_on 참조)",
    "test_030": "MES 시스템 의존 시스템: ERP, SCADA",
    "test_031": "ERP 웹서버~DB 경로: web-erp-XX -> was-erp-XX -> os-erp-XX -> srv-erp-XX -> db-erp-XX",
    "test_032": "MON~SCADA 경로: sys-mon -> sys-scada 그래프 탐색 결과",
    "test_033": "srv-erp-01~스토리지 경로: srv-erp-01 -> storage-erp",
    "test_034": "Analytics~ERP 연결: sys-analytics -> sys-erp (의존성)",
    "test_035": "CMDB~APM 최단 경로: sys-cmdb -> sys-apm (1-hop)",
    "test_036": "ERP 시스템 3-hop 이내: 179 nodes, 535 edges",
    "test_037": "MES 시스템 2단계 깊이: 137 nodes, 596 edges",
    "test_038": "SCADA 시스템 연결 서버: sys-scada 하위 모든 HW 서버",
    "test_039": "APM 의존 시스템: CMDB, SECOPS, ERP",
    "test_040": "CMDB 사용 시스템: APM, MON",
    "test_041": "ERP 시스템 WAS: was-erp-01 ~ was-erp-05 (5개)",
    "test_042": "MES 시스템 애플리케이션: app-mes-* 시리즈",
    "test_043": "시스템별 DB 개수: 약 40% 확률로 생성 (랜덤)",
    "test_044": "웹서버 연결 WAS: web-* -> was-* 관계",
    "test_045": "OS 위 실행 SW: os-* -> was-*, app-*, db-*",
    "test_046": "시스템 간 의존성 그래프: 8개 시스템 간 DEPENDS_ON 관계",
    "test_047": "핵심 시스템: APM, CMDB (가장 많은 의존)",
    "test_048": "ERP 장애 영향: Analytics (ERP 의존 시스템)",
    "test_049": "순환 의존성: APM <-> CMDB 등",
    "test_050": "MON 제거 영향: SCADA",
    # Metric Questions (51-75)
    "test_051": "CPU 사용량 최대 서버: metric_value cpu_usage 최신값 기준 (현재 데이터 없음)",
    "test_052": "메모리 80% 이상: memory_usage > 80 서버 (현재 데이터 없음)",
    "test_053": "1시간 평균 CPU: time_bucket 집계 (현재 데이터 없음)",
    "test_054": "최고 온도 서버: temperature 최대값 (현재 데이터 없음)",
    "test_055": "디스크 I/O TOP 5: disk_io 상위 5개 (현재 데이터 없음)",
    "test_056": "ERP 서버 24시간 CPU: '해당 기간에 메트릭 데이터가 없습니다' (실제 없음)",
    "test_057": "MES WAS 메모리: '해당 기간에 메트릭 데이터가 없습니다' (실제 없음)",
    "test_058": "7일간 온도 추세: temperature 7일 집계 (현재 데이터 없음)",
    "test_059": "1시간 네트워크 인바운드: '요청한 메트릭을 찾을 수 없습니다' (메트릭 정의 없음)",
    "test_060": "ERP DB CPU 시간대별: '해당 기간에 메트릭 데이터가 없습니다' (실제 없음)",
    "test_061": "CPU 평균 TOP 10: AVG(cpu_usage) GROUP BY ci_id (현재 데이터 없음)",
    "test_062": "메모리 최대 TOP 5: MAX(memory_usage) GROUP BY ci_id (현재 데이터 없음)",
    "test_063": "시스템별 평균 CPU: 시스템 태그 기준 AVG(cpu_usage) (현재 데이터 없음)",
    "test_064": "zone별 CPU 집계: location 기준 AVG(cpu_usage) (현재 데이터 없음)",
    "test_065": "OS별 평균 메모리: '해당 기간에 메트릭 데이터가 없습니다' (실제 없음)",
    "test_066": "오늘vs어제 CPU: 날짜별 AVG(cpu_usage) 비교 (현재 데이터 없음)",
    "test_067": "지난주vs이번주 CPU: 주별 AVG(cpu_usage) 차이 (현재 데이터 없음)",
    "test_068": "피크 시간대 CPU: 시간 11, 12시 필터 평균 (현재 데이터 없음)",
    "test_069": "주말vs평일 메모리: 요일별 AVG(memory_usage) 비교 (현재 데이터 없음)",
    "test_070": "새벽 디스크 I/O: '요청한 메트릭을 찾을 수 없습니다' (메트릭 정의 없음)",
    "test_071": "수집 가능한 메트릭: metric 테이블 name DISTINCT (약 5개)",
    "test_072": "cpu_usage 존재 여부: metric 테이블 name='cpu_usage' 확인 (있음)",
    "test_073": "temperature 메트릭 서버 수: metric 테이블 name='temperature' CI 개수",
    "test_074": "메트릭별 데이터 포인트: metric.name 기준 COUNT(*) FROM metric_value",
    "test_075": "quality='good' 비율: metric 테이블 quality='good' 비율",
    # History Questions (76-100)
    "test_076": "최근 24시간 작업 이력: work_history 테이블 (데이터 없음, Mock)",
    "test_077": "일주일 유지보수: maintenance_history 테이블 (데이터 없음, Mock)",
    "test_078": "오늘 장애 이력: event_log 테이블 (데이터 없음, Mock)",
    "test_079": "최근 변경 CI: ci 테이블 ORDER BY updated_at DESC (데이터 있음)",
    "test_080": "금주 배포 내역: work_history type='deployment' (데이터 없음, Mock)",
    "test_081": "ERP 유지보수 이력: maintenance_history WHERE ci LIKE '%erp%' (0 results)",
    "test_082": "patch 작업 최다 CI: work_history type='patch' GROUP BY ci_id (데이터 없음, Mock)",
    "test_083": "성공vs실패: work_history result='success' vs 'failure' COUNT (데이터 없음, Mock)",
    "test_084": "performer별 작업: work_history GROUP BY performer (데이터 없음, Mock)",
    "test_085": "최장 실행 유지보수: maintenance_history ORDER BY duration DESC (데이터 없음, Mock)",
    "test_086": "deployment 작업: work_history type='deployment' (데이터 없음, Mock)",
    "test_087": "alice 요청 작업: work_history requester='alice' (데이터 없음, Mock)",
    "test_088": "impact_level 5 작업: work_history impact_level=5 (데이터 없음, Mock)",
    "test_089": "승인된 실패: work_history approved=true AND result='failure' (데이터 없음, Mock)",
    "test_090": "사용자별 승인: work_history approved=true GROUP BY approver (데이터 없음, Mock)",
    "test_091": "12월 작업 수: work_history EXTRACT(MONTH)=12 COUNT (데이터 없음, Mock)",
    "test_092": "월별 유지보수: maintenance_history GROUP BY EXTRACT(MONTH) (데이터 없음, Mock)",
    "test_093": "작업 소요시간 평균: work_history AVG(duration) (데이터 없음, Mock)",
    "test_094": "주말 작업 수: work_history EXTRACT(DOW) IN (0,6) COUNT (데이터 없음, Mock)",
    "test_095": "시간대별 작업: work_history GROUP BY EXTRACT(HOUR) (데이터 없음, Mock)",
    "test_096": "시스템별 성공률: work_history result='success' 비율 (데이터 없음, Mock)",
    "test_097": "degraded 최다 CI: maintenance_history result='degraded' GROUP BY ci_id (데이터 없음, Mock)",
    "test_098": "자동화 작업 성공률: work_history is_automated=true 성공 비율 (데이터 없음, Mock)",
    "test_099": "작업유형별 평균 시간: work_history GROUP BY type ORDER BY AVG(duration) (데이터 없음, Mock)",
    "test_100": "30일간 실패 패턴: work_history result='failure' AND 30days 패턴 분석 (데이터 없음, Mock)",
}


def main():
    report_path = ROOT / "docs" / "UNIVERSAL_ORCHESTRATION_100Q_REPORT.md"

    with open(report_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        new_lines.append(line)

        # Find question header: ### N. test_XXX: Question
        if line.startswith("### ") and "test_" in line:
            # Extract test_id
            parts = line.strip().split()
            test_id = None
            for part in parts:
                if part.startswith("test_"):
                    test_id = part.rstrip(":")
                    break

            if test_id and test_id in EXPECTED_ANSWERS:
                # Skip lines until we find the closing ``` of the Answer section
                i += 1
                in_code_block = False
                code_block_count = 0

                while i < len(lines):
                    new_lines.append(lines[i])

                    if lines[i].strip() == "```":
                        code_block_count += 1
                        in_code_block = not in_code_block

                        # We've found the closing ```
                        if code_block_count == 2 and not in_code_block:
                            i += 1

                            # Add expected answer section
                            new_lines.append("\n")
                            new_lines.append(f"**Expected Answer**: {EXPECTED_ANSWERS[test_id]}\n")
                            new_lines.append("\n")
                            break
                    i += 1
        i += 1

    # Write updated content
    with open(report_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"✓ Expected answers added to {report_path}")


if __name__ == "__main__":
    main()
