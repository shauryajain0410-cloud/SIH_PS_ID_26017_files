export type RiskCategory = "High" | "Medium" | "Low";
export type RiskTier = RiskCategory; // Compatibility alias
export type UserRole = "admin" | "policymaker" | "project_manager";

export interface UserProfile {
  username: string;
  name: string;
  role: UserRole;
  region: string;
  department: string;
}

export interface ProjectListItem {
  project_id: string;
  quarter: string;
  region_final: string;
  sector_extracted: string;
  predicted_delay_probability: number;
  predicted_delay_pct: number;
  risk_category: RiskCategory;
  data_completeness: string;
  missing_field_count: number;
  original_cost_crore: number;
  physical_progress_pct: number;
  land_acquisition_pct: number;
  land_gap_ha_calc: number;
  top_contributing_drivers: string[];
}

// Legacy compatibility interface
export interface Project extends ProjectListItem {
  priority_score?: number;
  risk_tier?: RiskTier;
  top_delay_drivers?: string;
  recommended_actions?: string;
  previous_risk_tier?: string;
  previous_probability?: number;
  newly_high_risk?: boolean;
  run_timestamp?: string;
}

export interface ShapDriver {
  raw_feature: string;
  friendly_name: string;
  shap_value: number;
  impact: "increases_risk" | "reduces_risk";
  feature_value: number;
}

export interface KeywordHighlight {
  keyword_flag: string;
  friendly_flag_name: string;
  pattern: string;
  match_count: number;
}

export interface ProjectDetail {
  project_id: string;
  quarter: string;
  predicted_delay_probability: number;
  predicted_delay_pct: number;
  risk_category: RiskCategory;
  label_confidence_tier: string;
  feature_snapshot: {
    identity: {
      project_id: string;
      quarter: string;
      region: string;
      sector: string;
      state_freq_encoded: number;
      label_confidence_tier: string;
    };
    progress_and_cost: {
      original_cost_crore: number;
      anticipated_cost_crore: number;
      cost_overrun_pct: number;
      physical_progress_pct: number;
      project_age_months: number;
    };
    land_acquisition_status: {
      land_required_ha: number;
      land_acquired_ha: number;
      land_possession_ha: number;
      land_gap_ha: number;
      land_acquisition_pct: number;
      land_possession_pct: number;
      land_progress_ratio: number;
      has_land_component: boolean;
    };
    bottleneck_indicators: {
      legal_dispute_flag: boolean;
      compensation_mentioned: boolean;
      forest_or_clearance_issue: boolean;
      rr_issue_flag: boolean;
      row_issue_flag: boolean;
      administrative_issue_flag: boolean;
      num_compound_issues: number;
      has_delay_reason_text: boolean;
    };
  };
  shap_explanation: ShapDriver[];
  recommended_actions: string[];
  narrative: {
    raw_text: string;
    has_narrative: boolean;
    active_keyword_flags: KeywordHighlight[];
    character_length: number;
  };
  audit_record: {
    time_overrun_months: number;
    time_overrun_months_was_missing: boolean;
    ml_split_status: string;
    governance_note: string;
  };
}

export interface RegionBreakdown {
  region: string;
  total: number;
  high: number;
  medium: number;
  low: number;
}

export interface SectorBreakdown {
  sector: string;
  total: number;
  avg_probability: number;
}

export interface QuarterlyTrendPoint {
  quarter: string;
  total: number;
  avg_probability: number;
}

export interface OverviewData {
  total_projects: number;

  high_risk: number;
  medium_risk: number;
  low_risk: number;

  avg_delay_probability: number;

  by_region: {
    region: string;
    total: number;
    high: number;
    medium: number;
    low: number;
  }[];

  top_10_sectors: {
    sector: string;
    total: number;
    avg_probability: number;
  }[];

  all_sectors: string[];

  quarterly_trend: {
    quarter: string;
    total: number;
    avg_probability: number;
  }[];
}

export interface RegionSectorCount {
  region_final?: string;
  sector_extracted?: string;
  risk_tier: RiskTier;
  count: number;
}

export interface FeatureImportance {
  feature: string;
  importance: number;
}

export interface Summary {
  total_projects: number;
  high_risk: number;
  medium_risk: number;
  low_risk: number;
  by_region: RegionSectorCount[];
  by_sector: RegionSectorCount[];
  top_features: FeatureImportance[];
}

export interface RegionalBubble {
  region: string;
  lat: number;
  lng: number;
  total_projects: number;
  high_risk_count: number;
  high_risk_pct: number;
  avg_delay_probability: number;
  top_sectors: Record<string, number>;
  total_cost_crore?: number;
  avg_land_gap_ha?: number;
  avg_physical_progress?: number;
  critical_count?: number;
  top_delay_drivers?: string[];
}

export interface HeatmapMatrixCell {
  count: number;
  avg_prob: number;
  delay_rate: number;
}

export interface HeatmapMatrixRow {
  sector: string;
  regions: Record<string, HeatmapMatrixCell>;
}

export interface ProgressTimelinePoint {
  quarter: string;
  high_risk_physical_progress: number;
  ontrack_physical_progress: number;
  high_risk_land_complete_pct: number;
  ontrack_land_complete_pct: number;
}

export interface RegionalAnalyticsData {
  map_bubbles: RegionalBubble[];
  regions_list: string[];
  top_sectors: string[];
  heatmap_matrix: HeatmapMatrixRow[];
  timeline: ProgressTimelinePoint[];
  gis_governance_notice: string;
}

export interface AlertItem {
  alert_id: string;
  project_id: string;
  quarter: string;
  sector: string;
  region: string;
  predicted_delay_probability: number;
  predicted_delay_pct: number;
  severity: "CRITICAL" | "HIGH";
  primary_driver: string;
  label_confidence_tier: string;
  timestamp: string;
  recommended_actions?: string;
}

export interface ModelMetadata {
  model_type: string;
  problem_statement: string;
  target: string;
  split_methodology: string;
  excluded_features: string[];
  total_engineered_features: number;
  feature_names_sample: string[];
  test_set_evaluation: {
    test_samples: number;
    precision: number;
    recall: number;
    f1_score: number;
    roc_auc: number;
    pr_auc: number;
    confusion_matrix: {
      labels: string[];
      matrix: number[][];
      true_negatives: number;
      false_positives: number;
      false_negatives: number;
      true_positives: number;
    };
  };
  raw_test_metrics_log: string;
  retraining_instructions: string;
}

export interface NewProjectInput {
  project_id?: string;
  region_final: string;
  sector_extracted: string;
  original_cost_crore: number;
  anticipated_cost_crore_extracted?: number;
  physical_progress_pct?: number;
  project_age_months_at_report?: number;
  land_required_ha?: number;
  land_acquired_ha?: number;
  land_possession_ha?: number;
  compensation_mentioned: boolean;
  legal_dispute: boolean;
  forest_land_or_clearance_issue: boolean;
  rr_issue: boolean;
  row_issue: boolean;
  administrative_issue: boolean;
  covid_period: boolean;
  narrative_text?: string;
  scheduled_completion_date?: string;
  original_completion_date?: string;
  email?: string;
}

export interface NewProjectPrediction {
  project_id?: string;
  predicted_delay_probability: number; // 0-100
  risk_tier: RiskTier;
  priority_score: number;
  top_delay_drivers: string[];
  recommended_actions: string[];
  approximated_fields_used: string[];
}

