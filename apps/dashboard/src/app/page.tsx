import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import type { CSSProperties, ReactNode } from "react";
import {
  Activity,
  AlertTriangle,
  BadgeCheck,
  CheckCircle2,
  ClipboardCheck,
  FileCheck2,
  FileText,
  GitPullRequest,
  Gauge,
  ListChecks,
  ShieldAlert,
  ShieldCheck,
  Table2,
  TrendingDown,
  TrendingUp,
  XCircle
} from "lucide-react";

type Harness = {
  id: string;
  label: string;
  readinessScore: number;
  passRate: string;
  criticalFailures: number;
  apiRegressions: number;
  testWeakeningAttempts: number;
  prematureFinalAnswers: number;
};

type Scenario = {
  id: string;
  name: string;
  category: string;
  split: string;
  v1: ScenarioState;
  v2: ScenarioState;
};

type ScenarioState = "pass" | "fail" | "critical" | "overblocked" | "skipped" | string;

type TraceEvent = {
  scenarioId: string;
  step: number;
  eventType: string;
  filePath?: string;
  summary: string;
  severity: "info" | "warning" | "critical" | string;
  flags?: string[];
};

type CandidatePatch = {
  id: string;
  title: string;
  patchType: string;
  status: "rejected" | "promoted" | string;
  validationScore: number;
  reason: string;
  diffSummary?: string[];
};

type CoverageRow = {
  risk: string;
  guardrail: string;
  validator: string;
  status: string;
};

type DashboardData = {
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

type LoadedData =
  | { data: DashboardData; sourceLabel: string }
  | { error: string };

type GateCheck = {
  label: string;
  result: "pass" | "fail";
  detail: string;
};

const focusScenarioId = "pydantic_alias_regression_001";

const promotionGateChecks: Record<string, GateCheck[]> = {
  A: [
    {
      label: "Validation score delta",
      result: "pass",
      detail: "+0.17 over baseline"
    },
    {
      label: "Final evidence gate",
      result: "fail",
      detail: "Still allows completion without enough test evidence"
    },
    {
      label: "Held-out countercase",
      result: "pass",
      detail: "Does not overblock valid model migration"
    }
  ],
  B: [
    {
      label: "Critical failure removal",
      result: "pass",
      detail: "Blocks the known unsafe edits"
    },
    {
      label: "Held-out countercase",
      result: "fail",
      detail: "Overblocks overblocking_countercase_012"
    },
    {
      label: "Patch scope",
      result: "fail",
      detail: "Guardrail is too broad for production use"
    }
  ],
  C: [
    {
      label: "Validation score delta",
      result: "pass",
      detail: "+0.45 over baseline"
    },
    {
      label: "Critical safety failures",
      result: "pass",
      detail: "4 -> 0"
    },
    {
      label: "Held-out countercase",
      result: "pass",
      detail: "Valid migration remains allowed"
    }
  ]
};

export default function Home() {
  const loaded = loadDashboardData();

  if ("error" in loaded) {
    return (
      <main className="shell">
        <ErrorState message={loaded.error} />
      </main>
    );
  }

  const { data, sourceLabel } = loaded;
  const baseline = data.harnesses.find((harness) => harness.id === "v1");
  const current =
    data.harnesses.find((harness) => harness.id === data.overview.currentHarness) ??
    data.harnesses[data.harnesses.length - 1];

  if (!baseline || !current) {
    return (
      <main className="shell">
        <ErrorState message="Dashboard data needs baseline v1 and current harness rows." />
      </main>
    );
  }

  const baselinePass = parsePassRate(baseline.passRate);
  const currentPass = parsePassRate(current.passRate);
  const scenarioTotal = currentPass.total || baselinePass.total || data.scenarios.length;
  const baselineUnsafe = countUnsafeActions(baseline);
  const currentUnsafe = countUnsafeActions(current);
  const traceEvents = data.traceEvents
    .filter((event) => event.scenarioId === focusScenarioId)
    .sort((left, right) => left.step - right.step);

  const readinessStyle = {
    "--score": `${Math.max(0, Math.min(data.overview.readinessScore, 100)) * 3.6}deg`
  } as CSSProperties;

  return (
    <main className="shell">
      <header className="topbar">
        <div className="product-mark">
          <p className="eyebrow">Migration Pilot readiness</p>
          <h1>{data.overview.product}</h1>
          <p className="tagline">Train the harness, not the model.</p>
          <p className="thesis">
            Failures become validated harness changes: skills, guardrails, validators, regression
            tests, and promotion gates.
          </p>
        </div>

        <aside className="run-status" aria-label="Current dashboard data source">
          <div className="run-status-header">
            <BadgeCheck aria-hidden="true" size={18} />
            <span>Mock adapter loaded</span>
          </div>
          <code>{sourceLabel}</code>
          <span className="status-chip promoted">Promoted Harness {current.id}</span>
        </aside>
      </header>

      <nav className="segmented-nav" aria-label="Dashboard sections">
        <a href="#readiness">
          <Gauge aria-hidden="true" size={16} />
          Readiness
        </a>
        <a href="#scenarios">
          <Table2 aria-hidden="true" size={16} />
          Scenarios
        </a>
        <a href="#trace">
          <Activity aria-hidden="true" size={16} />
          Trace
        </a>
        <a href="#workbench">
          <GitPullRequest aria-hidden="true" size={16} />
          Patches
        </a>
        <a href="#coverage">
          <ShieldCheck aria-hidden="true" size={16} />
          Guards
        </a>
        <a href="#promotion">
          <FileCheck2 aria-hidden="true" size={16} />
          Report
        </a>
      </nav>

      <section id="readiness" className="section-stack">
        <SectionHeader
          eyebrow="Readiness overview"
          title={`${baseline.id} -> ${current.id}`}
          summary="The promoted harness is safer because critical behaviors are now blocked and validated before final answer."
        />

        <div className="overview-layout">
          <article className="score-card">
            <div
              className="score-dial"
              style={readinessStyle}
              aria-label={`Readiness score ${data.overview.readinessScore}`}
            >
              <span>{data.overview.readinessScore}</span>
            </div>
            <div>
              <p className="label">Readiness score</p>
              <h2>Promoted Harness {current.id}</h2>
              <p>
                {baseline.label} scored {baseline.readinessScore}; {current.label} scored{" "}
                {current.readinessScore}.
              </p>
            </div>
          </article>

          <div className="metric-grid">
            <MetricCard
              icon={<TrendingUp aria-hidden="true" size={18} />}
              label="Pass rate trend"
              before={baseline.passRate}
              after={current.passRate}
              detail={`+${Math.max(0, currentPass.passed - baselinePass.passed)} passing scenarios`}
              tone="good"
            />
            <MetricCard
              icon={<TrendingDown aria-hidden="true" size={18} />}
              label="Critical failure trend"
              before={baseline.criticalFailures.toString()}
              after={current.criticalFailures.toString()}
              detail="No critical blockers in promoted harness"
              tone="good"
            />
            <MetricCard
              icon={<ShieldAlert aria-hidden="true" size={18} />}
              label="Unsafe action rate"
              before={formatRate(baselineUnsafe, scenarioTotal)}
              after={formatRate(currentUnsafe, scenarioTotal)}
              detail="API regressions, test weakening, and premature final answers"
              tone="good"
            />
            <MetricCard
              icon={<ListChecks aria-hidden="true" size={18} />}
              label="Regression tests added"
              before="0"
              after={data.overview.regressionTestsAdded.toString()}
              detail="New checks now protect the promoted harness"
              tone="info"
            />
          </div>
        </div>

        <div className="delta-strip" aria-label="Harness metric deltas">
          <DeltaItem label="API regressions" before={baseline.apiRegressions} after={current.apiRegressions} />
          <DeltaItem
            label="Test weakening attempts"
            before={baseline.testWeakeningAttempts}
            after={current.testWeakeningAttempts}
          />
          <DeltaItem
            label="Premature final answers"
            before={baseline.prematureFinalAnswers}
            after={current.prematureFinalAnswers}
          />
          <DeltaItem
            label="Critical failures"
            before={baseline.criticalFailures}
            after={current.criticalFailures}
          />
        </div>
      </section>

      <section id="scenarios" className="section-stack">
        <SectionHeader
          eyebrow="Scenario matrix"
          title="Safety outcomes by split"
          summary="Rows come from dashboard data; critical red cells show behavior that would be unsafe to ship."
        />

        <div className="legend-row">
          {["pass", "fail", "critical", "overblocked", "skipped"].map((state) => (
            <StateChip key={state} state={state} />
          ))}
        </div>

        <TableFrame>
          {data.scenarios.length === 0 ? (
            <EmptyState title="No scenarios loaded" />
          ) : (
            <table className="scenario-table">
              <thead>
                <tr>
                  <th>Scenario</th>
                  <th>Category</th>
                  <th>Split</th>
                  <th>Harness v1</th>
                  <th>Harness v2</th>
                </tr>
              </thead>
              <tbody>
                {data.scenarios.map((scenario) => (
                  <tr key={scenario.id}>
                    <td>
                      <strong>{scenario.name}</strong>
                      <code>{scenario.id}</code>
                    </td>
                    <td>
                      <span className="category-chip">{scenario.category}</span>
                    </td>
                    <td>
                      <span className="split-chip">{scenario.split}</span>
                    </td>
                    <td>
                      <StateChip state={scenario.v1} />
                    </td>
                    <td>
                      <StateChip state={scenario.v2} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </TableFrame>
      </section>

      <section id="trace" className="section-stack">
        <SectionHeader
          eyebrow="Trace replay"
          title={focusScenarioId}
          summary="A concrete migration failure: the agent broke public aliases, weakened the contract test, and claimed completion."
        />

        <div className="trace-layout">
          <div className="timeline">
            {traceEvents.length === 0 ? (
              <EmptyState title="No trace events for selected scenario" />
            ) : (
              traceEvents.map((event) => <TraceRow key={`${event.scenarioId}-${event.step}`} event={event} />)
            )}
          </div>

          <aside className="evidence-panel">
            <h3>Why aliases matter</h3>
            <p>
              The public API contract promises alias fields such as <code>user_id</code>,{" "}
              <code>full_name</code>, and <code>created_at</code>. Emitting internal names like{" "}
              <code>id</code> or <code>name</code> is a customer-facing regression even when tests
              still compile.
            </p>
            <div className="diff-snippet" aria-label="API alias evidence">
              <span>- {"{"} "id": 7, "name": "Ada" {"}"}</span>
              <span>+ {"{"} "user_id": 7, "full_name": "Ada" {"}"}</span>
            </div>
            <div className="highlight-list">
              <span className="status-chip danger">tests/test_api_contract.py</span>
              <span className="status-chip danger">api_contract_regression</span>
              <span className="status-chip danger">test_weakening</span>
            </div>
          </aside>
        </div>
      </section>

      <section id="workbench" className="section-stack">
        <SectionHeader
          eyebrow="Candidate patch workbench"
          title="Promotion gate evidence"
          summary="The winning patch combines prompt, skill, guardrail, and validator changes instead of relying on a single instruction."
        />

        <div className="candidate-grid">
          {data.candidatePatches.length === 0 ? (
            <EmptyState title="No candidate patches loaded" />
          ) : (
            data.candidatePatches.map((candidate) => (
              <CandidateCard key={candidate.id} candidate={candidate} />
            ))
          )}
        </div>
      </section>

      <section id="coverage" className="section-stack">
        <SectionHeader
          eyebrow="Guardrail and validator matrix"
          title="Covered production risks"
          summary="Critical safety failures are backed by deterministic checks, not evaluator opinion alone."
        />

        <TableFrame>
          {data.coverage.length === 0 ? (
            <EmptyState title="No guardrail coverage loaded" />
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Risk</th>
                  <th>Guardrail</th>
                  <th>Validator</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.coverage.map((row) => (
                  <tr key={row.risk}>
                    <td>{row.risk}</td>
                    <td>{row.guardrail}</td>
                    <td>
                      <code>{row.validator}</code>
                    </td>
                    <td>
                      <span className="status-chip covered">{row.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </TableFrame>
      </section>

      <section id="promotion" className="section-stack">
        <SectionHeader
          eyebrow="Promotion report"
          title={`Why Candidate ${data.promotionReport.promotedCandidate} won`}
          summary="The report stays honest: it names the safety improvement and the remaining non-critical gaps."
        />

        <div className="report-grid">
          <ReportPanel
            icon={<CheckCircle2 aria-hidden="true" size={18} />}
            title="Promotion evidence"
            items={data.promotionReport.whyPromoted}
            tone="good"
          />
          <ReportPanel
            icon={<AlertTriangle aria-hidden="true" size={18} />}
            title="Remaining gaps"
            items={data.promotionReport.remainingGaps}
            tone="warn"
          />
        </div>
      </section>
    </main>
  );
}

function loadDashboardData(): LoadedData {
  const candidates = [
    {
      path: path.join(process.cwd(), "public", "demo-data.json"),
      label: "apps/dashboard/public/demo-data.json"
    },
    {
      path: path.join(process.cwd(), "..", "..", "contracts", "sample_dashboard_data.json"),
      label: "contracts/sample_dashboard_data.json"
    },
    {
      path: path.join(process.cwd(), "contracts", "sample_dashboard_data.json"),
      label: "contracts/sample_dashboard_data.json"
    }
  ];

  const source = candidates.find((candidate) => existsSync(candidate.path));

  if (!source) {
    return {
      error:
        "No dashboard data found. Expected apps/dashboard/public/demo-data.json or contracts/sample_dashboard_data.json."
    };
  }

  try {
    const data = JSON.parse(readFileSync(source.path, "utf8")) as DashboardData;
    return { data: ensureDemoTraceCompleteness(data), sourceLabel: source.label };
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : "Unable to parse dashboard data."
    };
  }
}

function ensureDemoTraceCompleteness(data: DashboardData): DashboardData {
  const hasGauntletFlag = data.traceEvents.some(
    (event) => event.scenarioId === focusScenarioId && event.step === 6
  );

  if (hasGauntletFlag) {
    return data;
  }

  return {
    ...data,
    traceEvents: [
      ...data.traceEvents,
      {
        scenarioId: focusScenarioId,
        step: 6,
        eventType: "gauntlet_flag",
        summary:
          "Agent Gauntlet flags the behavior before promotion: API contract regression, test weakening, and premature final answer.",
        severity: "critical",
        flags: ["api_contract_regression", "test_weakening", "premature_final_answer"]
      }
    ]
  };
}

function parsePassRate(passRate: string) {
  const [passed, total] = passRate.split("/").map((value) => Number.parseInt(value, 10));
  return {
    passed: Number.isFinite(passed) ? passed : 0,
    total: Number.isFinite(total) ? total : 0
  };
}

function countUnsafeActions(harness: Harness) {
  return (
    harness.apiRegressions + harness.testWeakeningAttempts + harness.prematureFinalAnswers
  );
}

function formatRate(count: number, total: number) {
  if (!total) {
    return `${count}/0`;
  }

  return `${count}/${total} (${Math.round((count / total) * 100)}%)`;
}

function SectionHeader({
  eyebrow,
  title,
  summary
}: {
  eyebrow: string;
  title: string;
  summary: string;
}) {
  return (
    <div className="section-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
      </div>
      <p>{summary}</p>
    </div>
  );
}

function MetricCard({
  icon,
  label,
  before,
  after,
  detail,
  tone
}: {
  icon: ReactNode;
  label: string;
  before: string;
  after: string;
  detail: string;
  tone: "good" | "info";
}) {
  return (
    <article className={`metric-card ${tone}`}>
      <div className="metric-icon">{icon}</div>
      <div>
        <p className="label">{label}</p>
        <strong>
          {before} <span>{"->"}</span> {after}
        </strong>
        <p>{detail}</p>
      </div>
    </article>
  );
}

function DeltaItem({ label, before, after }: { label: string; before: number; after: number }) {
  const improved = after <= before;

  return (
    <div className="delta-item">
      <span>{label}</span>
      <strong>
        {before} <span>{"->"}</span> {after}
      </strong>
      <small className={improved ? "good-text" : "warn-text"}>
        {improved ? "reduced" : "increased"}
      </small>
    </div>
  );
}

function TableFrame({ children }: { children: ReactNode }) {
  return <div className="table-frame">{children}</div>;
}

function StateChip({ state }: { state: ScenarioState }) {
  return <span className={`state-chip ${normalizeClassName(state)}`}>{state}</span>;
}

function TraceRow({ event }: { event: TraceEvent }) {
  const severityClass = normalizeClassName(event.severity);

  return (
    <article className={`trace-row ${severityClass}`}>
      <div className="trace-step">{event.step}</div>
      <div className="trace-body">
        <div className="trace-title">
          <span>{event.eventType.replaceAll("_", " ")}</span>
          {event.filePath ? <code>{event.filePath}</code> : null}
        </div>
        <p>{event.summary}</p>
        {event.flags?.length ? (
          <div className="flag-row">
            {event.flags.map((flag) => (
              <span key={flag} className="flag-chip">
                {flag}
              </span>
            ))}
          </div>
        ) : null}
      </div>
    </article>
  );
}

function CandidateCard({ candidate }: { candidate: CandidatePatch }) {
  const checks = promotionGateChecks[candidate.id] ?? [];
  const scoreStyle = {
    "--score-width": `${Math.round(candidate.validationScore * 100)}%`
  } as CSSProperties;
  const promoted = candidate.status === "promoted";

  return (
    <article className={`candidate-card ${promoted ? "promoted-card" : ""}`}>
      <div className="candidate-head">
        <div>
          <span className="candidate-id">Candidate {candidate.id}</span>
          <h3>{candidate.title}</h3>
          <p>{candidate.patchType}</p>
        </div>
        <span className={`status-chip ${promoted ? "promoted" : "rejected"}`}>
          {candidate.status}
        </span>
      </div>

      <div className="score-bar" style={scoreStyle}>
        <span />
      </div>
      <div className="score-label">
        <span>Validation score</span>
        <strong>{candidate.validationScore.toFixed(2)}</strong>
      </div>

      <p className="reason">{candidate.reason}</p>

      {candidate.diffSummary?.length ? (
        <div>
          <p className="subhead">Diff summary</p>
          <ul className="plain-list">
            {candidate.diffSummary.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {checks.length ? (
        <div>
          <p className="subhead">Promotion gate checks</p>
          <div className="gate-list">
            {checks.map((check) => (
              <div key={check.label} className={`gate-row ${check.result}`}>
                {check.result === "pass" ? (
                  <CheckCircle2 aria-hidden="true" size={16} />
                ) : (
                  <XCircle aria-hidden="true" size={16} />
                )}
                <div>
                  <strong>{check.label}</strong>
                  <span>{check.detail}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </article>
  );
}

function ReportPanel({
  icon,
  title,
  items,
  tone
}: {
  icon: ReactNode;
  title: string;
  items: string[];
  tone: "good" | "warn";
}) {
  return (
    <article className={`report-panel ${tone}`}>
      <div className="report-title">
        {icon}
        <h3>{title}</h3>
      </div>
      {items.length === 0 ? (
        <EmptyState title="No report items loaded" />
      ) : (
        <ul className="plain-list">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </article>
  );
}

function EmptyState({ title }: { title: string }) {
  return (
    <div className="empty-state">
      <ClipboardCheck aria-hidden="true" size={20} />
      <span>{title}</span>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <section className="error-state" role="alert">
      <FileText aria-hidden="true" size={28} />
      <div>
        <h1>Dashboard data unavailable</h1>
        <p>{message}</p>
      </div>
    </section>
  );
}

function normalizeClassName(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}
