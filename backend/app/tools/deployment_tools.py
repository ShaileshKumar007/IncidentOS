import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.config import DEMO_WORKSPACE_ROOT
from app.schemas.common import ToolExecutionResult
from app.schemas.tools import DeploymentRecord, DeploymentSearchResponse
from app.tools.workspace import resolve_and_validate_path


def parse_iso_timestamp(ts_str: Optional[str]) -> Optional[datetime]:
    if not ts_str:
        return None
    try:
        clean_ts = ts_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_ts)
    except Exception:
        return None


def get_deployment_history(
    service: Optional[str] = None,
    version: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    incident_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    demo_root: Optional[Path] = None,
) -> DeploymentSearchResponse:
    start_tick = time.perf_counter()
    root = (demo_root or DEMO_WORKSPACE_ROOT).resolve()

    start_dt = parse_iso_timestamp(start_time)
    end_dt = parse_iso_timestamp(end_time)

    deployments: List[DeploymentRecord] = []
    rel_path = "deployments/history.json"

    try:
        validated_file = resolve_and_validate_path(
            rel_path,
            allowed_dirs=["deployments"],
            demo_root=root,
        )
    except Exception:
        validated_file = None

    if validated_file and validated_file.exists():
        with open(validated_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    # Filter service
                    if service and item.get("service", "").lower() != service.lower():
                        continue

                    # Filter version
                    if version and item.get("version", "").lower() != version.lower():
                        continue

                    # Filter timestamp
                    dep_dt = parse_iso_timestamp(item.get("deployed_at"))
                    if start_dt and dep_dt and dep_dt < start_dt:
                        continue
                    if end_dt and dep_dt and dep_dt > end_dt:
                        continue

                    rec = DeploymentRecord(
                        deployment_id=item.get("deployment_id", "dep-unknown"),
                        service=item.get("service", "unknown"),
                        version=item.get("version", "0.0.0"),
                        environment=item.get("environment", "unknown"),
                        deployed_at=item.get("deployed_at", ""),
                        status=item.get("status", "SUCCESS"),
                        commit_hash=item.get("commit_hash", ""),
                        deployer=item.get("deployer", ""),
                        release_notes=item.get("release_notes"),
                        synthetic_marker=item.get("synthetic_marker"),
                    )
                    deployments.append(rec)

    duration_ms = (time.perf_counter() - start_tick) * 1000.0
    audit = ToolExecutionResult(
        tool_name="deployments.get_history",
        incident_id=incident_id,
        agent_id=agent_id,
        status="SUCCESS",
        duration_ms=round(duration_ms, 2),
        result_summary=f"Retrieved {len(deployments)} deployment records.",
    )

    return DeploymentSearchResponse(
        total_deployments=len(deployments),
        deployments=deployments,
        audit=audit,
    )
