#!/usr/bin/env python3
"""Test script for PDF report generation."""

import sys
import os

# Add the app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.modules.ops.services.report_service import pdf_report_service


def test_simple_pdf():
    """Test simple PDF generation."""
    print("Testing simple PDF generation...")

    # Create sample data
    summary = "This is a test summary of the conversation."

    metadata = {
        "title": "Test OPS Report",
        "topic": "Testing PDF Generation",
        "date": "2026-02-11",
    }

    blocks = [
        {
            "type": "text",
            "content": "This is a sample text block in the PDF report."
        },
        {
            "type": "table",
            "title": "Sample Data",
            "columns": ["Name", "Value", "Status"],
            "rows": [
                ["Item 1", "100", "OK"],
                ["Item 2", "200", "Warning"],
                ["Item 3", "300", "Error"],
            ]
        }
    ]

    try:
        pdf_content = pdf_report_service.generate_summary_report(
            summary=summary,
            metadata=metadata,
            blocks=blocks
        )

        # Save to file
        output_path = "/tmp/test_ops_report.pdf"
        with open(output_path, "wb") as f:
            f.write(pdf_content)

        print(f"PDF generated successfully!")
        print(f"   Size: {len(pdf_content)} bytes")
        print(f"   Saved to: {output_path}")
        return True

    except Exception as e:
        print(f"PDF generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_simple_pdf()

    # Also test conversation report
    print("\n" + "="*50)
    print("Testing conversation PDF generation...")

    sample_conversation = {
        "title": "MES Server 06 성능 분석",
        "topic": "OPS 시스템 성능 모니터링",
        "date": "2026-02-11",
        "questions_and_answers": [
            {
                "question": "MES Server 06의 CPU 사용률이 80%를 넘고 있는데, 이상 징후가 있는지 확인해줘",
                "timestamp": "2026-02-11 14:30:00",
                "mode": "metric",
                "summary": "CPU 사용률 평균 45%로 정상 범위입니다.",
                "blocks": [
                    {
                        "type": "chart",
                        "title": "CPU 사용률 트렌드",
                        "summary": "최근 24시간 동안 CPU 사용률은 평균 45%로 안정적입니다."
                    },
                    {
                        "type": "table",
                        "title": "메트릭 상세",
                        "columns": ["시간", "CPU 사용률", "Memory 사용률"],
                        "rows": [
                            ["14:00", "42%", "55%"],
                            ["14:10", "45%", "56%"],
                            ["14:20", "48%", "57%"],
                        ]
                    }
                ]
            }
        ]
    }

    try:
        pdf_content = pdf_report_service.generate_conversation_report(sample_conversation)
        output_path = "/tmp/test_conversation_report.pdf"
        with open(output_path, "wb") as f:
            f.write(pdf_content)
        print(f"✅ Conversation PDF generated successfully!")
        print(f"   Size: {len(pdf_content)} bytes")
        print(f"   Saved to: {output_path}")
    except Exception as e:
        print(f"❌ Conversation PDF failed: {e}")
        import traceback
        traceback.print_exc()
