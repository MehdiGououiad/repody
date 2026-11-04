from tests.integration.helpers import condition, invoice_workflow, rule


async def test_create_save_and_read(api):
    created = (await api.post("/v1/workflows", json={"name": "Draft"})).json()
    assert created["status"] == "draft"
    assert len(created["documents"]) == 1

    body = invoice_workflow(rule("total", condition("total_amount", "==", "6000")))
    saved = await api.put(f"/v1/workflows/{created['id']}", json=body)
    assert saved.status_code == 200, saved.text
    workflow = (await api.get(f"/v1/workflows/{created['id']}")).json()
    assert workflow["documents"][0]["schema"][0]["templateType"] == "number"
    left = workflow["rules"][0]["conditions"][0]["left"]
    assert left == {"kind": "field", "value": "total_amount"}

    listed = (await api.get("/v1/workflows")).json()["workflows"]
    assert [w["id"] for w in listed] == [created["id"]]
    assert listed[0]["documents"] == []  # list cards carry no definition


async def test_save_rejects_incomplete_rules_and_duplicate_fields(api):
    incomplete = invoice_workflow(rule("r", condition("", "==")))
    response = await api.put("/v1/workflows/wf-x", json=incomplete)
    assert response.status_code == 422
    assert "Choose a field on the left" in response.json()["detail"]

    duplicate = invoice_workflow()
    duplicate["documents"][0]["schema"].append({"id": "f3", "name": "TVA"})
    assert (await api.put("/v1/workflows/wf-x", json=duplicate)).status_code == 422


async def test_check_rules(api):
    body = invoice_workflow(
        rule("ok", condition("total_amount", ">=", "100")),
        rule("todo", condition("total_amount", "==")),
    )
    rules = (await api.post("/v1/workflows/check-rules", json=body)).json()["rules"]
    assert rules[0] == {"ruleId": "ok", "issues": [], "checks": ["total_amount >= 100"]}
    assert rules[1]["checks"] == [""]
    assert rules[1]["issues"]


async def test_deploy_and_archive(api):
    await api.put("/v1/workflows/wf-d", json=invoice_workflow())
    deployed = (await api.post("/v1/workflows/wf-d/deploy")).json()
    assert deployed["status"] == "active"
    assert deployed["apiKey"].startswith("wbk_live_")
    assert deployed["apiStats"]["apiCallsTotal"] == 0
    assert (await api.get("/v1/workflows/wf-d")).json()["apiKey"] is None

    assert (await api.post("/v1/workflows/bulk-delete", json={"ids": ["wf-d"]})).status_code == 204
    assert (await api.get("/v1/workflows/wf-d")).status_code == 404
