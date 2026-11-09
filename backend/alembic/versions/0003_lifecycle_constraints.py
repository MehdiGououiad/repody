"""Lifecycle constraints: every run, rule result and workflow is in a state its lifecycle has.

A workflow's status follows its deployment (active means deployed); "paused" was never set
by the app and becomes active or draft. See repody.app.lifecycle and docs/LIFECYCLES.md.

Revision ID: 0003
Revises: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE workflows SET status = CASE WHEN status = 'archived' THEN 'archived' "
        "WHEN deployed_at IS NOT NULL THEN 'active' ELSE 'draft' END"
    )
    op.create_check_constraint(
        "ck_workflows_status",
        "workflows",
        "status IN ('draft', 'active', 'archived') "
        "AND (status = 'archived' OR (status = 'active') = (deployed_at IS NOT NULL))",
    )
    op.create_check_constraint(
        "ck_runs_status", "runs", "status IN ('queued', 'running', 'done', 'failed')"
    )
    op.create_check_constraint(
        "ck_runs_outcome",
        "runs",
        "(outcome IS NOT NULL) = (status = 'done') "
        "AND (outcome IS NULL OR outcome IN ('passed', 'warning', 'failed'))",
    )
    op.create_check_constraint(
        "ck_rule_results_status", "rule_results", "status IN ('passed', 'failed', 'skipped')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_rule_results_status", "rule_results", type_="check")
    op.drop_constraint("ck_runs_outcome", "runs", type_="check")
    op.drop_constraint("ck_runs_status", "runs", type_="check")
    op.drop_constraint("ck_workflows_status", "workflows", type_="check")
