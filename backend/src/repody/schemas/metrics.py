from pydantic import Field

from repody.schemas.common import CamelModel


class KpiSeriesPoint(CamelModel):
    day: str
    value: float


class KpiMetric(CamelModel):
    id: str
    label: str
    value: str
    raw_value: float
    delta: float
    delta_unit: str
    direction: str
    positive: bool
    series: list[KpiSeriesPoint]
    icon: str


class PerformancePoint(CamelModel):
    day: str
    runs: int
    prev_runs: int


class ViolationBreakdown(CamelModel):
    type: str
    share: float
    color: str


class HealthAlert(CamelModel):
    id: str
    severity: str
    title_key: str
    detail_key: str
    href: str | None = None


class MetricsResponse(CamelModel):
    kpis: list[KpiMetric]
    performance_series: list[PerformancePoint]
    violation_breakdown: list[ViolationBreakdown]
    health_alerts: list[HealthAlert] = Field(default_factory=list)
