import {
  OverviewData,
  ProjectListItem,
  ProjectDetail,
  RegionalAnalyticsData,
  AlertItem,
  ModelMetadata,
  UserProfile,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

function getAuthHeader(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("sih_auth_token");
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

export async function fetchOverview(): Promise<OverviewData> {
  const res = await fetch(`${API_BASE}/api/overview`, {
    headers: { ...getAuthHeader() },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Overview fetch failed: ${res.statusText}`);
  return res.json();
}

export async function fetchProjects(params?: {
  region?: string;
  sector?: string;
  risk?: string;
  data_completeness?: string;
  search?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: string;
}): Promise<{
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  projects: ProjectListItem[];
}> {
  const url = new URL(`${API_BASE}/api/projects`);

  if (params) {
    if (params.region && params.region !== "All") {
      url.searchParams.set("region", params.region);
    }

    if (params.sector && params.sector !== "All") {
      url.searchParams.set("sector", params.sector);
    }

    if (params.risk && params.risk !== "All") {
      url.searchParams.set("risk", params.risk);
    }

    if (params.data_completeness && params.data_completeness !== "All") {
      url.searchParams.set("data_completeness", params.data_completeness);
    }

    if (params.search) {
      url.searchParams.set("search", params.search);
    }

    if (params.page) {
      url.searchParams.set("page", params.page.toString());
    }

    if (params.page_size) {
      url.searchParams.set("page_size", params.page_size.toString());
    }

    if (params.sort_by) {
      url.searchParams.set("sort_by", params.sort_by);
    }

    if (params.sort_order) {
      url.searchParams.set("sort_order", params.sort_order);
    }
  }

  const res = await fetch(url.toString(), {
    headers: { ...getAuthHeader() },
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`Projects fetch failed: ${res.statusText}`);
  }

  const data = await res.json();

  const projects: ProjectListItem[] = (data.projects || []).map(
    (p: any) => {
      let probability = Number(
        p.predicted_delay_probability ?? 0
      );

      // Normalize either 0–1 or 0–100 input
      if (probability > 1) {
        probability = probability / 100;
      }

      probability = Math.max(0, Math.min(1, probability));

      const riskValue =
        p.risk_category ??
        p.risk_tier ??
        "Low";

      const normalizedRisk =
        String(riskValue).toLowerCase() === "high"
          ? "High"
          : String(riskValue).toLowerCase() === "medium"
          ? "Medium"
          : "Low";

      let drivers: string[] = [];

      if (Array.isArray(p.top_contributing_drivers)) {
        drivers = p.top_contributing_drivers;
      } else if (Array.isArray(p.top_delay_drivers)) {
        drivers = p.top_delay_drivers;
      } else if (typeof p.top_delay_drivers === "string") {
        drivers = p.top_delay_drivers
          .split(";")
          .map((x: string) => x.trim())
          .filter(Boolean);
      }

      return {
        project_id: String(p.project_id ?? ""),
        quarter: String(p.quarter ?? ""),
        region_final: String(
          p.region_final ?? p.region ?? "Unknown"
        ),
        sector_extracted: String(
          p.sector_extracted ?? p.sector ?? "Unknown"
        ),

        predicted_delay_probability: probability,
        predicted_delay_pct: probability * 100,

        risk_category: normalizedRisk,

        data_completeness: String(p.data_completeness ?? "Sparse Data"),
        missing_field_count: Number(p.missing_field_count ?? 0),

        original_cost_crore: Number(
          p.original_cost_crore ?? 0
        ),

        physical_progress_pct: Number(
          p.physical_progress_pct ?? 0
        ),

        land_acquisition_pct: Number(
          p.land_acquisition_pct ?? 0
        ),

        land_gap_ha_calc: Number(
          p.land_gap_ha_calc ?? 0
        ),

        top_contributing_drivers: drivers,
      };
    }
  );

  return {
    total_count: Number(data.total_count ?? projects.length),
    page: Number(data.page ?? 1),
    page_size: Number(data.page_size ?? projects.length),
    total_pages: Number(data.total_pages ?? 1),
    projects,
  };
}

export async function fetchProjectDetail(
  projectId: string
): Promise<ProjectDetail> {
  const res = await fetch(
    `${API_BASE}/projects/${encodeURIComponent(projectId)}/explanation`,
    {
      headers: { ...getAuthHeader() },
      cache: "no-store",
    }
  );

  if (res.status === 403) {
    throw new Error(
      "Policymaker role restricted: Narrative drill-down restricted to maintain aggregate policy focus."
    );
  }

  if (!res.ok) {
    throw new Error(
      `Project detail fetch failed: ${res.statusText}`
    );
  }

  return res.json();
}

export async function fetchRegionalAnalytics(): Promise<RegionalAnalyticsData> {
  const res = await fetch(`${API_BASE}/api/regional`, {
    headers: { ...getAuthHeader() },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Regional analytics fetch failed: ${res.statusText}`);
  return res.json();
}

export async function fetchAlerts(minProb: number = 0.65): Promise<{
  alert_count: number;
  threshold_probability: number;
  alerts: AlertItem[];
}> {
  const res = await fetch(`${API_BASE}/api/alerts?min_probability=${minProb}`, {
    headers: { ...getAuthHeader() },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Alerts fetch failed: ${res.statusText}`);
  return res.json();
}

export async function fetchModelMetadata(): Promise<ModelMetadata> {
  const res = await fetch(`${API_BASE}/api/model/metadata`, {
    headers: { ...getAuthHeader() },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Model metadata fetch failed: ${res.statusText}`);
  return res.json();
}

export async function postPredict(payload: Record<string, any>): Promise<any> {
  const res = await fetch(`${API_BASE}/api/predict`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Prediction API failed: ${res.statusText}`);
  return res.json();
}

export async function loginApi(username: string, password: string): Promise<{
  access_token: string;
  token_type: string;
  user: UserProfile;
}> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw new Error("Invalid username or password");
  return res.json();
}

import { NewProjectInput, NewProjectPrediction } from "./types";

export async function predictNewProject(
  input: NewProjectInput
): Promise<NewProjectPrediction> {
  const response = await fetch(`${API_BASE}/predict-new-project`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ? JSON.stringify(body.detail) : "Prediction request failed");
  }

  return response.json();
}
