import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from app.config import DEMO_WORKSPACE_ROOT, MAX_LOG_RESULTS
from app.schemas.common import ToolExecutionResult
from app.schemas.tools import LogRecord, LogSearchResponse
from app.tools.workspace import resolve_and_validate_path


def parse_iso_timestamp(ts_str: Optional[str]) -> Optional[datetime]:
    if not ts_str:
        return None
    try:
        # Handle 'Z' suffix or standard ISO formats
        clean_ts = ts_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_ts)
    except Exception:
        return None


def search_logs(
    service: Optional[str] = None,
    severity: Optional[str] = None,
    keyword: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 50,
    incident_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    demo_root: Optional[Path] = None,
) -> LogSearchResponse:
    start_tick = time.perf_counter()
    root = (demo_root or DEMO_WORKSPACE_ROOT).resolve()
    logs_dir = root / "logs"

    limit = min(max(1, limit), MAX_LOG_RESULTS)
    start_dt = parse_iso_timestamp(start_time)
    end_dt = parse_iso_timestamp(end_time)

    records: List[LogRecord] = []
    total_matches = 0

    if logs_dir.exists() and logs_dir.is_dir():
        # Read all permitted log files in the logs directory
        for log_file in sorted(logs_dir.glob("*.jsonl")):
            # Validate through workspace security
            try:
                rel_path = str(log_file.relative_to(root))
                validated_file = resolve_and_validate_path(
                    rel_path,
                    allowed_dirs=["logs"],
                    demo_root=root,
                )
            except Exception:
                continue

            with open(validated_file, "r", encoding="utf-8") as f:
                for line_no, raw_line in enumerate(f, start=1):
                    line_str = raw_line.strip()
                    if not line_str:
                        continue
                    try:
                        data = json.loads(line_str)
                    except json.JSONDecodeError:
                        continue

                    # Filter by service
                    if service and data.get("service", "").lower() != service.lower():
                        continue

                    # Filter by severity / level
                    if severity and data.get("level", "").upper() != severity.upper():
                        continue

                    # Filter by timestamp
                    record_dt = parse_iso_timestamp(data.get("timestamp"))
                    if start_dt and record_dt and record_dt < start_dt:
                        continue
                    if end_dt and record_dt and record_dt > end_dt:
                        continue

                    # Filter by keyword
                    if keyword:
                        kw_lower = keyword.lower()
                        msg = data.get("message", "").lower()
                        stack = data.get("stack_trace", "").lower()
                        logger = data.get("logger", "").lower()
                        err_type = data.get("error_type", "").lower()
                        if (
                            kw_lower not in msg
                            and kw_lower not in stack
                            and kw_lower not in logger
                            and kw_lower not in err_type
                        ):
                            continue

                    total_matches += 1
                    if len(records) < limit:
                        rec = LogRecord(
                            log_id=data.get("log_id") or f"log-{validated_file.stem}-{line_no}",
                            timestamp=data.get("timestamp", ""),
                            level=data.get("level", "INFO"),
                            service=data.get("service", "unknown"),
                            logger=data.get("logger"),
                            message=data.get("message", ""),
                            trace_id=data.get("trace_id"),
                            source_file=data.get("culprit_class") or str(validated_file.relative_to(root)),
                            line_number=data.get("line_number"),
                            stack_trace=data.get("stack_trace"),
                            context=data.get("context"),
                        )
                        records.append(rec)

    duration_ms = (time.perf_counter() - start_tick) * 1000.0
    audit = ToolExecutionResult(
        tool_name="logs.search",
        incident_id=incident_id,
        agent_id=agent_id,
        status="SUCCESS",
        duration_ms=round(duration_ms, 2),
        result_summary=f"Found {total_matches} logs matching criteria (returned {len(records)}).",
    )

    return LogSearchResponse(
        total_matches=total_matches,
        returned_count=len(records),
        records=records,
        audit=audit,
    )


def get_log_by_id(
    log_id: str,
    incident_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    demo_root: Optional[Path] = None,
) -> Tuple[Optional[LogRecord], ToolExecutionResult]:
    start_tick = time.perf_counter()
    root = (demo_root or DEMO_WORKSPACE_ROOT).resolve()
    logs_dir = root / "logs"

    found_record: Optional[LogRecord] = None

    if logs_dir.exists() and logs_dir.is_dir():
        for log_file in sorted(logs_dir.glob("*.jsonl")):
            try:
                rel_path = str(log_file.relative_to(root))
                validated_file = resolve_and_validate_path(
                    rel_path,
                    allowed_dirs=["logs"],
                    demo_root=root,
                )
            except Exception:
                continue

            with open(validated_file, "r", encoding="utf-8") as f:
                for line_no, raw_line in enumerate(f, start=1):
                    line_str = raw_line.strip()
                    if not line_str:
                        continue
                    try:
                        data = json.loads(line_str)
                    except json.JSONDecodeError:
                        continue

                    current_id = data.get("log_id") or f"log-{validated_file.stem}-{line_no}"
                    if current_id == log_id or data.get("trace_id") == log_id:
                        found_record = LogRecord(
                            log_id=current_id,
                            timestamp=data.get("timestamp", ""),
                            level=data.get("level", "INFO"),
                            service=data.get("service", "unknown"),
                            logger=data.get("logger"),
                            message=data.get("message", ""),
                            trace_id=data.get("trace_id"),
                            source_file=data.get("culprit_class") or str(validated_file.relative_to(root)),
                            line_number=data.get("line_number"),
                            stack_trace=data.get("stack_trace"),
                            context=data.get("context"),
                        )
                        break
            if found_record:
                break

    duration_ms = (time.perf_counter() - start_tick) * 1000.0
    status = "SUCCESS" if found_record else "ERROR"
    summary = f"Log record {log_id} found." if found_record else f"Log record {log_id} not found."

    audit = ToolExecutionResult(
        tool_name="logs.get_by_id",
        incident_id=incident_id,
        agent_id=agent_id,
        status=status,
        duration_ms=round(duration_ms, 2),
        result_summary=summary,
        error=None if found_record else f"Log ID '{log_id}' not found.",
    )

    return found_record, audit
