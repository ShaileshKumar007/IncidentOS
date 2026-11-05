from app.tools.log_tools import get_log_by_id, search_logs


def test_search_logs_all(temp_workspace):
    res = search_logs(demo_root=temp_workspace)
    assert res.total_matches >= 3
    assert res.returned_count >= 3
    assert res.audit.status == "SUCCESS"
    assert res.audit.tool_name == "logs.search"


def test_search_logs_filter_severity(temp_workspace):
    res = search_logs(severity="ERROR", demo_root=temp_workspace)
    assert res.returned_count >= 2
    for record in res.records:
        assert record.level == "ERROR"


def test_search_logs_filter_keyword(temp_workspace):
    res = search_logs(keyword="NullPointerException", demo_root=temp_workspace)
    assert res.returned_count >= 2
    for record in res.records:
        assert "NullPointerException" in record.message or (record.stack_trace and "NullPointerException" in record.stack_trace)


def test_search_logs_filter_service(temp_workspace):
    res = search_logs(service="checkout-service", demo_root=temp_workspace)
    assert res.returned_count >= 3
    for record in res.records:
        assert record.service == "checkout-service"


def test_search_logs_filter_time_range(temp_workspace):
    # Filter after 22:02
    res = search_logs(start_time="2026-11-04T22:02:00Z", demo_root=temp_workspace)
    assert res.returned_count >= 2
    # Records at 22:00 should not be returned
    for record in res.records:
        assert record.timestamp >= "2026-11-04T22:02:00Z"


def test_search_logs_no_match(temp_workspace):
    res = search_logs(keyword="NONEXISTENT_KEYWORD_XYZ", demo_root=temp_workspace)
    assert res.total_matches == 0
    assert len(res.records) == 0


def test_get_log_by_id_found(temp_workspace):
    rec, audit = get_log_by_id("err-001", demo_root=temp_workspace)
    assert rec is not None
    assert rec.log_id == "err-001"
    assert rec.level == "ERROR"
    assert audit.status == "SUCCESS"


def test_get_log_by_trace_id(temp_workspace):
    rec, audit = get_log_by_id("tr-001", demo_root=temp_workspace)
    assert rec is not None
    assert rec.trace_id == "tr-001"
    assert audit.status == "SUCCESS"


def test_get_log_by_id_not_found(temp_workspace):
    rec, audit = get_log_by_id("fake-id-999", demo_root=temp_workspace)
    assert rec is None
    assert audit.status == "ERROR"


def test_api_log_endpoints(client, temp_workspace, monkeypatch):
    import app.tools.log_tools as log_mod
    monkeypatch.setattr(log_mod, "DEMO_WORKSPACE_ROOT", temp_workspace)

    # Search endpoint
    resp = client.get("/api/tools/logs/search?severity=ERROR&keyword=NullPointerException")
    assert resp.status_code == 200
    data = resp.json()
    assert data["returned_count"] >= 1
    assert "audit" in data

    # Detail endpoint
    resp2 = client.get("/api/tools/logs/err-001")
    assert resp2.status_code == 200
    assert resp2.json()["log_id"] == "err-001"

    # Detail 404
    resp3 = client.get("/api/tools/logs/nonexistent-id")
    assert resp3.status_code == 404
