from __future__ import annotations

from tests.conftest import bearer, issue_token, setup_project


def test_dispatch_model_snapshot_pinning_policy(client):
    officer = issue_token(client, "Tenant-Model-Policy", "officer@modelpolicy.test", ["officer"], clearance="restricted")
    _, _, project_id = setup_project(client, officer)

    profiles_res = client.put(
        f"/v1/projects/{project_id}/policy-profiles",
        headers=bearer(officer),
        json={
            "profiles": {
                "model": {
                    "enforce_snapshot_pinning": True,
                    "allowed_snapshot_patterns": [r".*-\d{4}-\d{2}-\d{2}$", r".*\.\d+(\.\d+)?$"],
                    "blocked_aliases": ["gpt-5"],
                    "require_eval_for_promotion": True,
                    "min_eval_score_bp": 8000,
                }
            }
        },
    )
    assert profiles_res.status_code == 200, profiles_res.text

    blocked = client.post(
        "/v1/dispatch",
        headers=bearer(officer),
        json={
            "project_id": project_id,
            "target_scope": "group",
            "target_value": "workers",
            "provider": "openai_codex",
            "model": "gpt-5",
            "payload": {"prompt": "ping"},
        },
    )
    assert blocked.status_code == 422, blocked.text
    assert "snapshot pinning policy violation" in blocked.text

    allowed = client.post(
        "/v1/dispatch",
        headers=bearer(officer),
        json={
            "project_id": project_id,
            "target_scope": "group",
            "target_value": "workers",
            "provider": "openai_codex",
            "model": "gpt-5.4",
            "payload": {"prompt": "ping"},
        },
    )
    assert allowed.status_code == 200, allowed.text


def test_eval_required_before_model_promotion_and_deployment(client):
    officer = issue_token(client, "Tenant-Model-Gate", "officer@modelgate.test", ["officer"], clearance="restricted")
    _, _, project_id = setup_project(client, officer)

    fine_tune = client.post(
        "/v1/models/fine-tunes",
        headers=bearer(officer),
        json={
            "project_id": project_id,
            "provider": "openai_codex",
            "base_model": "gpt-5.4",
            "target_model": "gpt-5.4-ordl-v1",
            "dataset_uri": "s3://ordl/datasets/train-v1.jsonl",
            "dataset_digest": "sha256:abc123",
            "dataset_provenance": {
                "source": "internal_corpus",
                "collection_method": "curated",
                "rights_basis": "owned_or_licensed",
            },
            "training_params": {"epochs": 3},
        },
    )
    assert fine_tune.status_code == 200, fine_tune.text

    blocked_promotion = client.post(
        "/v1/models/promotions",
        headers=bearer(officer),
        json={
            "project_id": project_id,
            "provider": "openai_codex",
            "model": "gpt-5.4-ordl-v1",
            "environment": "staging",
            "fine_tune_run_id": fine_tune.json()["id"],
            "mode": "promote",
        },
    )
    assert blocked_promotion.status_code == 409, blocked_promotion.text
    detail = blocked_promotion.json().get("detail", {})
    assert detail.get("reason") == "eval_gate_failed"
    assert "missing_eval_run" in detail.get("reason_codes", [])

    eval_run = client.post(
        "/v1/models/evals/runs",
        headers=bearer(officer),
        json={
            "project_id": project_id,
            "provider": "openai_codex",
            "model": "gpt-5.4-ordl-v1",
            "suite_name": "release",
            "score_bp": 9100,
            "threshold_bp": 8500,
            "status": "pass",
            "metrics": {"accuracy": 0.91},
            "findings": [],
        },
    )
    assert eval_run.status_code == 200, eval_run.text

    promoted = client.post(
        "/v1/models/promotions",
        headers=bearer(officer),
        json={
            "project_id": project_id,
            "provider": "openai_codex",
            "model": "gpt-5.4-ordl-v1",
            "environment": "staging",
            "fine_tune_run_id": fine_tune.json()["id"],
            "eval_run_id": eval_run.json()["id"],
            "mode": "promote",
        },
    )
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["status"] == "approved"

    deployed = client.post(
        "/v1/models/deployments",
        headers=bearer(officer),
        json={
            "project_id": project_id,
            "provider": "openai_codex",
            "model": "gpt-5.4-ordl-v1",
            "environment": "production",
            "eval_run_id": eval_run.json()["id"],
            "mode": "promote",
        },
    )
    assert deployed.status_code == 200, deployed.text
    assert deployed.json()["status"] == "deployed"

