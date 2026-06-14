export interface KpiMetric {
  id: string;
  label: string;
  value: string;
  rawValue: number;
  delta: number;
  deltaUnit: string;
  direction: string;
  positive: boolean;
  series: { day: string; value: number }[];
  icon: string;
}

export interface PerformancePoint {
  day: string;
  runs: number;
  prevRuns: number;
}

export interface ViolationBreakdown {
  type: string;
  share: number;
  color: string;
}

export interface MetricsResponse {
  kpis: KpiMetric[];
  performanceSeries: PerformancePoint[];
  violationBreakdown: ViolationBreakdown[];
}
