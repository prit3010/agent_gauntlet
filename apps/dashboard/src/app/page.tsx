import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { FileText } from "lucide-react";
import DashboardClient from "./DashboardClient";
import type { DashboardData, LoadedData } from "./dashboard-types";

const focusScenarioId = "pydantic_alias_regression_001";

export default function Home() {
  const loaded = loadDashboardData();

  if ("error" in loaded) {
    return (
      <main className="shell">
        <section className="error-state" role="alert">
          <FileText aria-hidden="true" size={24} />
          <div>
            <h1>Dashboard data unavailable</h1>
            <p>{loaded.error}</p>
          </div>
        </section>
      </main>
    );
  }

  return <DashboardClient data={loaded.data} />;
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
