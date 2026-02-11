"""PDF report generation service for OPS conversations.

Generates professional PDF reports from OPS query results and conversations.
"""

import io
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)


class PDFReportService:
    """Service for generating PDF reports from OPS conversations."""

    # Page dimensions
    PAGE_WIDTH, PAGE_HEIGHT = A4
    MARGIN = 1.5 * cm

    # Colors
    PRIMARY_COLOR = colors.HexColor("#2563EB")  # Blue
    HEADER_BG = colors.HexColor("#1E40AF")  # Dark blue
    TEXT_COLOR = colors.HexColor("#1F2937")  # Dark gray
    BORDER_COLOR = colors.HexColor("#E5E7EB")  # Light gray

    @staticmethod
    def _create_styles() -> Dict[str, ParagraphStyle]:
        """Create custom paragraph styles for the report."""
        styles = getSampleStyleSheet()

        return {
            "title": ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=24,
                textColor=colors.white,
                spaceAfter=0.5 * cm,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            ),
            "subtitle": ParagraphStyle(
                "CustomSubtitle",
                parent=styles["Heading2"],
                fontSize=14,
                textColor=colors.HexColor("#6B7280"),
                spaceAfter=1 * cm,
                alignment=TA_CENTER,
            ),
            "heading2": ParagraphStyle(
                "CustomHeading2",
                parent=styles["Heading2"],
                fontSize=16,
                textColor=PDFReportService.PRIMARY_COLOR,
                spaceBefore=0.8 * cm,
                spaceAfter=0.3 * cm,
                fontName="Helvetica-Bold",
            ),
            "heading3": ParagraphStyle(
                "CustomHeading3",
                parent=styles["Heading3"],
                fontSize=13,
                textColor=PDFReportService.TEXT_COLOR,
                spaceBefore=0.5 * cm,
                spaceAfter=0.2 * cm,
                fontName="Helvetica-Bold",
            ),
            "normal": ParagraphStyle(
                "CustomNormal",
                parent=styles["Normal"],
                fontSize=10,
                textColor=PDFReportService.TEXT_COLOR,
                spaceAfter=0.3 * cm,
                leading=14,
            ),
            "small": ParagraphStyle(
                "CustomSmall",
                parent=styles["Normal"],
                fontSize=9,
                textColor=colors.HexColor("#6B7280"),
                spaceAfter=0.2 * cm,
                leading=12,
            ),
            "metadata": ParagraphStyle(
                "Metadata",
                parent=styles["Normal"],
                fontSize=10,
                textColor=colors.HexColor("#374151"),
                leftIndent=0.5 * cm,
            ),
        }

    @staticmethod
    def _create_header_footer(canvas, doc):
        """Create header and footer for each page."""
        # Save state
        canvas.saveState()

        # Header - colored background bar
        canvas.setFillColor(PDFReportService.HEADER_BG)
        canvas.rect(
            0,
            PDFReportService.PAGE_HEIGHT - 1.2 * cm,
            PDFReportService.PAGE_WIDTH,
            1.2 * cm,
            fill=1,
            stroke=0,
        )

        # Header text
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawString(
            2 * cm,
            PDFReportService.PAGE_HEIGHT - 0.8 * cm,
            "TOBIT OPS Report",
        )

        canvas.setFont("Helvetica", 9)
        canvas.drawString(
            PDFReportService.PAGE_WIDTH - 3 * cm,
            PDFReportService.PAGE_HEIGHT - 0.8 * cm,
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        )

        # Footer - line and page number
        canvas.setFillColor(PDFReportService.BORDER_COLOR)
        canvas.rect(
            0,
            1.2 * cm,
            PDFReportService.PAGE_WIDTH,
            0.5 * mm,
            fill=1,
            stroke=0,
        )

        canvas.setFillColor(colors.HexColor("#6B7280"))
        canvas.setFont("Helvetica", 8)
        page_num = canvas.getPageNumber()
        canvas.drawCentredString(
            PDFReportService.PAGE_WIDTH / 2,
            0.8 * cm,
            f"Page {page_num}",
        )

        # Restore state
        canvas.restoreState()

    @staticmethod
    def _create_metadata_table(metadata: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> Table:
        """Create metadata information table."""
        data = [
            [Paragraph("<b>제목 (Title)</b>", styles["normal"]), Paragraph(metadata.get("title", "-"), styles["normal"])],
            [Paragraph("<b>일자 (Date)</b>", styles["normal"]), Paragraph(metadata.get("date", datetime.now().strftime("%Y-%m-%d")), styles["normal"])],
            [Paragraph("<b>주제 (Topic)</b>", styles["normal"]), Paragraph(metadata.get("topic", "-"), styles["normal"])],
            [Paragraph("<b>생성일 (Generated)</b>", styles["normal"]), Paragraph(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"), styles["normal"])],
        ]

        table = Table(data, colWidths=[4 * cm, 11 * cm])
        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), PDFReportService.BORDER_COLOR),
                ("TEXTCOLOR", (0, 0), (0, -1), PDFReportService.TEXT_COLOR),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, PDFReportService.BORDER_COLOR),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ])
        )

        return table

    @staticmethod
    def _create_qa_section(
        questions_and_answers: List[Dict[str, Any]],
        styles: Dict[str, ParagraphStyle]
    ) -> List[Any]:
        """Create Q&A section from conversation history."""
        elements = []

        for idx, qa in enumerate(questions_and_answers, 1):
            # Question heading
            elements.append(Paragraph(f"Q{idx}. {qa.get('question', '')}", styles["heading2"]))

            # Question metadata
            if qa.get("timestamp"):
                elements.append(Paragraph(
                    f"<i>질문일시: {qa['timestamp']}</i>",
                    styles["small"]
                ))
                elements.append(Spacer(1, 0.2 * cm))

            # Mode badge
            if qa.get("mode"):
                elements.append(Paragraph(
                    f"<b>모드:</b> {qa['mode']}",
                    styles["metadata"]
                ))

            # Summary (if available)
            if qa.get("summary"):
                elements.append(Paragraph("<b>요약:</b>", styles["heading3"]))
                elements.append(Paragraph(qa["summary"], styles["normal"]))

            # Process blocks
            blocks = qa.get("blocks", [])
            if blocks:
                # Add content blocks
                for block in blocks:
                    block_type = block.get("type", "")
                    elements = PDFReportService._add_block_to_elements(
                        block, elements, styles
                    )

            # References (if available)
            if qa.get("references"):
                elements.append(Paragraph("<b>참고 자료:</b>", styles["heading3"]))
                for ref in qa["references"][:5]:  # Limit to 5 references
                    elements.append(Paragraph(f"• {ref.get('title', ref.get('text', ''))}", styles["small"]))

            elements.append(Spacer(1, 0.5 * cm))

        return elements

    @staticmethod
    def _add_block_to_elements(block: Dict[str, Any], elements: List[Any], styles: Dict[str, ParagraphStyle]) -> List[Any]:
        """Add a single block to the elements list."""
        block_type = block.get("type", "")

        if block_type == "text":
            if block.get("content"):
                elements.append(Paragraph(block["content"], styles["normal"]))

        elif block_type == "table":
            # Add table
            columns = block.get("columns", [])
            rows = block.get("rows", [])

            if columns and rows:
                # Header row
                table_data = [[Paragraph(f"<b>{col}</b>", styles["small"]) for col in columns]]

                # Data rows (limit to 20 rows for PDF)
                for row in rows[:20]:
                    table_data.append([Paragraph(str(cell), styles["small"]) for cell in row])

                table = Table(table_data, repeatRows=1)
                table.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), PDFReportService.PRIMARY_COLOR),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("GRID", (0, 0), (-1, -1), 0.5, PDFReportService.BORDER_COLOR),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ])
                )
                elements.append(table)
                elements.append(Spacer(1, 0.3 * cm))

                # Add note if rows were truncated
                if len(rows) > 20:
                    elements.append(
                        Paragraph(f"<i>* 테이블이 너무 길어 처음 20행만 표시됩니다 (총 {len(rows)}행)</i>", styles["small"])
                    )

        elif block_type == "chart":
            # Add chart placeholder/title
            if block.get("title"):
                elements.append(Paragraph(f"<b>[차트]</b> {block['title']}", styles["metadata"]))
            if block.get("summary"):
                elements.append(Paragraph(block["summary"], styles["normal"]))

        elif block_type == "graph":
            # Add graph description
            if block.get("summary"):
                elements.append(Paragraph(f"<b>[그래프]</b> {block['summary']}", styles["normal"]))
            if block.get("node_count"):
                elements.append(
                    Paragraph(
                        f"노드 수: {block['node_count']}, 엣지 수: {block.get('edge_count', 'N/A')}",
                        styles["small"]
                    )
                )

        elif block_type == "summary":
            if block.get("title"):
                elements.append(Paragraph(f"<b>{block['title']}</b>", styles["heading3"]))
            if block.get("content"):
                elements.append(Paragraph(block["content"], styles["normal"]))

        return elements

    @staticmethod
    def generate_conversation_report(
        conversation_data: Dict[str, Any],
        title: Optional[str] = None
    ) -> bytes:
        """
        Generate PDF report from conversation data.

        Args:
            conversation_data: Dictionary containing conversation information
                - title: Report title
                - topic: Main topic/subject
                - date: Report date
                - questions_and_answers: List of Q&A entries
            title: Optional override title

        Returns:
            PDF content as bytes
        """
        try:
            # Create buffer
            buffer = io.BytesIO()

            # Create document
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                leftMargin=PDFReportService.MARGIN,
                rightMargin=PDFReportService.MARGIN,
                topMargin=2 * cm,
                bottomMargin=2 * cm,
            )

            # Get styles
            styles = PDFReportService._create_styles()

            # Build story (content elements)
            story = []

            # Title page
            story.append(Spacer(1, 2 * cm))
            story.append(
                Paragraph(
                    title or conversation_data.get("title", "OPS 대화 보고서"),
                    styles["title"]
                )
            )
            story.append(
                Paragraph(
                    "TOBIT Operations Intelligence System",
                    styles["subtitle"]
                )
            )
            story.append(Spacer(1, 1 * cm))

            # Metadata table
            metadata = {
                "title": conversation_data.get("title", ""),
                "topic": conversation_data.get("topic", "OPS 분석"),
                "date": conversation_data.get("date", datetime.now().strftime("%Y-%m-%d")),
            }
            story.append(PDFReportService._create_metadata_table(metadata, styles))
            story.append(Spacer(1, 1 * cm))

            # Page break before content
            story.append(PageBreak())

            # Q&A Section
            questions_and_answers = conversation_data.get("questions_and_answers", [])
            if questions_and_answers:
                story.append(Paragraph("질의-응답 내역", styles["heading2"]))
                story.append(Spacer(1, 0.3 * cm))

                elements = PDFReportService._create_qa_section(
                    questions_and_answers, styles
                )
                story.extend(elements)

            # Summary section (if available)
            if conversation_data.get("overall_summary"):
                story.append(PageBreak())
                story.append(Paragraph("종합 요약", styles["heading2"]))
                story.append(
                    Paragraph(
                        conversation_data["overall_summary"],
                        styles["normal"]
                    )
                )

            # Build PDF
            doc.build(
                story,
                onFirstPage=PDFReportService._create_header_footer,
                onLaterPages=PDFReportService._create_header_footer,
            )

            # Get PDF content
            pdf_content = buffer.getvalue()
            buffer.close()

            logger.info(f"Generated PDF report: {len(pdf_content)} bytes")
            return pdf_content

        except Exception as e:
            logger.error(f"Failed to generate PDF report: {e}", exc_info=True)
            raise

    @staticmethod
    def generate_summary_report(
        summary: str,
        metadata: Dict[str, Any],
        blocks: Optional[List[Dict[str, Any]]] = None
    ) -> bytes:
        """
        Generate a simple PDF summary report.

        Args:
            summary: Summary text
            metadata: Metadata (title, date, topic, etc.)
            blocks: Optional content blocks to include

        Returns:
            PDF content as bytes
        """
        try:
            buffer = io.BytesIO()

            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                leftMargin=PDFReportService.MARGIN,
                rightMargin=PDFReportService.MARGIN,
                topMargin=2 * cm,
                bottomMargin=2 * cm,
            )

            styles = PDFReportService._create_styles()
            story = []

            # Title
            story.append(Spacer(1, 2 * cm))
            story.append(
                Paragraph(
                    metadata.get("title", "OPS 요약 보고서"),
                    styles["title"]
                )
            )
            story.append(Spacer(1, 1 * cm))

            # Metadata
            story.append(PDFReportService._create_metadata_table(metadata, styles))
            story.append(Spacer(1, 1 * cm))

            # Summary
            story.append(Paragraph("요약 내용", styles["heading2"]))
            story.append(Paragraph(summary, styles["normal"]))
            story.append(Spacer(1, 0.5 * cm))

            # Blocks (if provided)
            if blocks:
                story.append(Paragraph("상세 내용", styles["heading2"]))
                for block in blocks:
                    story = PDFReportService._add_block_to_elements(
                        block, story, styles
                    )

            # Build PDF
            doc.build(
                story,
                onFirstPage=PDFReportService._create_header_footer,
                onLaterPages=PDFReportService._create_header_footer,
            )

            pdf_content = buffer.getvalue()
            buffer.close()

            return pdf_content

        except Exception as e:
            logger.error(f"Failed to generate summary PDF: {e}", exc_info=True)
            raise


# Global service instance
pdf_report_service = PDFReportService()
