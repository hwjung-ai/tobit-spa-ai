"""Data export service for dashboard and query results.

Supports CSV and JSON export formats.
"""

import csv
import io
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DataExporter:
    """Handles data export to various formats."""

    @staticmethod
    def export_to_csv(
        data: List[Dict[str, Any]],
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Export data to CSV format.
        
        Args:
            data: List of dictionaries to export
            filename: Optional filename (defaults to timestamp)
            
        Returns:
            Dict with filename and content
        """
        try:
            if not data:
                raise ValueError("No data to export")

            # Generate filename
            if filename is None:
                filename = f"export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

            # Create CSV in memory
            output = io.StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=data[0].keys(),
                extrasaction='ignore'
            )
            writer.writeheader()
            writer.writerows(data)

            return {
                "filename": filename,
                "content": output.getvalue(),
                "content_type": "text/csv",
                "size": len(output.getvalue())
            }

        except Exception as e:
            logger.error(f"CSV export failed: {e}", exc_info=True)
            raise

    @staticmethod
    def export_to_json(
        data: List[Dict[str, Any]],
        filename: Optional[str] = None,
        pretty: bool = True
    ) -> Dict[str, Any]:
        """
        Export data to JSON format.
        
        Args:
            data: List of dictionaries to export
            filename: Optional filename (defaults to timestamp)
            pretty: Whether to pretty-print JSON
            
        Returns:
            Dict with filename and content
        """
        try:
            if not data:
                raise ValueError("No data to export")

            # Generate filename
            if filename is None:
                filename = f"export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

            # Convert to JSON
            indent = 2 if pretty else None
            content = json.dumps(data, indent=indent, default=str, ensure_ascii=False)

            return {
                "filename": filename,
                "content": content,
                "content_type": "application/json",
                "size": len(content)
            }

        except Exception as e:
            logger.error(f"JSON export failed: {e}", exc_info=True)
            raise

    @staticmethod
    def export_observability_data(
        data: Dict[str, Any],
        format_type: str = "csv"
    ) -> Dict[str, Any]:
        """
        Export observability dashboard data.
        
        Args:
            data: Observability data (KPIs, stats, timeline, errors)
            format_type: Export format (csv, json, excel)
            
        Returns:
            Dict with filename and content
        """
        try:
            # Flatten nested data for export
            flattened_data = []

            # Export KPIs
            if "kpis" in data:
                for key, value in data["kpis"].items():
                    flattened_data.append({
                        "metric": key,
                        "value": value,
                        "timestamp": datetime.utcnow().isoformat(),
                        "category": "kpi"
                    })

            # Export stats
            if "stats" in data:
                for key, value in data["stats"].items():
                    if isinstance(value, dict):
                        for subkey, subvalue in value.items():
                            flattened_data.append({
                                "metric": f"{key}.{subkey}",
                                "value": subvalue,
                                "timestamp": datetime.utcnow().isoformat(),
                                "category": "stats"
                            })
                    else:
                        flattened_data.append({
                            "metric": key,
                            "value": value,
                            "timestamp": datetime.utcnow().isoformat(),
                            "category": "stats"
                        })

            # Export timeline
            if "timeline" in data:
                for item in data["timeline"]:
                    flattened_data.append({
                        "metric": "event",
                        "event_type": item.get("event_type", ""),
                        "status": item.get("status", ""),
                        "timestamp": item.get("timestamp", ""),
                        "category": "timeline"
                    })

            # Export errors
            if "errors" in data:
                for error in data["errors"]:
                    flattened_data.append({
                        "metric": "error",
                        "error_type": error.get("error_type", ""),
                        "error_message": error.get("error_message", ""),
                        "timestamp": error.get("timestamp", ""),
                        "category": "errors"
                    })

            # Export based on format
            if format_type == "csv":
                return DataExporter.export_to_csv(
                    flattened_data,
                    filename=f"observability_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
                )
            elif format_type == "json":
                return DataExporter.export_to_json(
                    flattened_data,
                    filename=f"observability_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
                )
            else:
                raise ValueError(f"Unsupported format: {format_type}. Supported formats: csv, json")

        except Exception as e:
            logger.error(f"Observability data export failed: {e}", exc_info=True)
            raise

    @staticmethod
    def export_query_result(
        result: Dict[str, Any],
        format_type: str = "csv"
    ) -> Dict[str, Any]:
        """
        Export query result.
        
        Args:
            result: Query result data
            format_type: Export format (csv, json, excel)
            
        Returns:
            Dict with filename and content
        """
        try:
            # Extract table data
            data = []

            # Handle different result types
            if result.get("type") == "table":
                data = result.get("rows", [])
            elif result.get("type") == "timeseries":
                # Flatten timeseries data
                for point in result.get("data", []):
                    data.append({
                        "timestamp": point.get("timestamp"),
                        **point.get("values", {})
                    })
            elif result.get("type") == "metric":
                # Flatten metric data
                for key, value in result.get("value", {}).items():
                    data.append({
                        "metric": key,
                        "value": value,
                        "timestamp": result.get("timestamp", datetime.utcnow().isoformat())
                    })
            else:
                # Generic export
                data = [result]

            # Generate filename
            query_type = result.get("type", "query")
            filename_base = f"{query_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

            # Export based on format
            if format_type == "csv":
                return DataExporter.export_to_csv(
                    data,
                    filename=f"{filename_base}.csv"
                )
            elif format_type == "json":
                return DataExporter.export_to_json(
                    data,
                    filename=f"{filename_base}.json"
                )
            else:
                raise ValueError(f"Unsupported format: {format_type}. Supported formats: csv, json")

        except Exception as e:
            logger.error(f"Query result export failed: {e}", exc_info=True)
            raise


# Global exporter instance
data_exporter = DataExporter()
