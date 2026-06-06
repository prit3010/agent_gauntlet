export type Harness = {
  id: string;
  label: string;
  readinessScore: number;
  passRate: string;
  criticalFailures: number;
  apiRegressions: number;
  testWeakeningAttempts: number;
  prematureFinalAnswers: number;
};

export type ScenarioState = "pass" | "fail" | "critical" | "overblocked" | "skipped" | string;

export type Scenario = {
  id: string;
  name: string;
  category: string;
  split: string;
  v1: ScenarioState;
  v2: ScenarioState;
};

export type TraceEvent = {
  scenarioId: string;
  step: number;
  eventType: string;
  filePath?: string;
  summary: string;
  severity: "info" | "warning" | "critical" | string;
  flags?: string[];
};

export type CandidatePatch = {
  id: string;
  title: string;
  patchType: string;
  status: "rejected" | "promoted" | string;
  validationScore: number;
  reason: string;
  diffSummary?: string[];
};

export type CoverageRow = {
  risk: string;
  guardrail: string;
  validator: string;
  status: string;
};

export type DashboardData = {
  overview: {
    product: string;
    currentHarness: string;
    readinessScore: number;
    passRate: string;
    criticalFailures: number;
    apiRegressions: number;
    testWeakeningAttempts: number;
    regressionTestsAdded: number;
  };
  harnesses: Harness[];
  scenarios: Scenario[];
  traceEvents: TraceEvent[];
  candidatePatches: CandidatePatch[];
  coverage: CoverageRow[];
  promotionReport: {
    promotedCandidate: string;
    whyPromoted: string[];
    remainingGaps: string[];
  };
};

export type LoadedData =
  | { data: DashboardData; sourceLabel: string }
  | { error: string };
