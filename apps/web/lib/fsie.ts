// Types and English display copy for the Hong Kong FSIE research prototype.
// Field and node keys come from packages/contracts (the fact dictionary and
// JUDGEMENT_CHAIN); this file only maps them to readable English.

export type TerminalState = "research_only_output" | "human_review_required" | "stop_and_escalate";
export type NodeOutput =
  | "satisfied"
  | "not_satisfied"
  | "unknown"
  | "conflict"
  | "condition_not_demonstrated"
  | "human_review_required";

export interface FactRow {
  field: string;
  value: string | number | boolean | null;
  status: "ai_candidate" | "unknown" | "conflict";
  domain: string | null;
  data_type: string | null;
  blocking_level: string | null;
  related_nodes: string[];
  statute_locator: string | null;
}

export interface ChainRow {
  node: string;
  ordinal: number;
  implemented: boolean;
  rule_id: string | null;
  output: NodeOutput | null;
  blockers: string[];
  escalation_blockers: string[];
  note: string | null;
  source_ids: string[];
  statute_locators: string[];
}

export interface AnalysisResult {
  case_id: string;
  execution_batch: string;
  model: string;
  prompt_version: string;
  repair_rounds: number;
  rule_set_version: string;
  rule_set_status: string;
  git_commit: string | null;
  facts: FactRow[];
  terminal_state: TerminalState;
  blockers: string[];
  conflict_fields: string[];
  chain: ChainRow[];
  statute_units: { locator: string; text: string }[];
  sources: { source_id: string; title: string | null; url: string | null }[];
  watermark: string;
  timing_ms: { extraction: number; total: number };
}

export interface SampleCase {
  id: string;
  title: string;
  tag: string;
  maps_to: string | null;
  expected_state: TerminalState | null;
  text: string;
}

export interface Meta {
  release_level: string;
  rule_set_version: string | null;
  rule_set_status: string;
  chain_nodes_total: number;
  chain_nodes_implemented: number;
  sources_registered: number;
  sources_parsed: number;
  legal_units: number;
  legal_coverage_cutoff: string | null;
  model: string | null;
}

export const WATERMARK_EN =
  "L0 internal research prototype. Candidate rules are unverified by a Hong Kong tax professional. Not tax advice; not for client use.";

export const FIELD_LABELS: Record<string, string> = {
  entity_hk_business_status: "Carries on business in Hong Kong",
  mne_group_status: "MNE entity (member of a multinational group)",
  regulated_financial_entity_status: "Regulated financial entity",
  pure_equity_holding_entity_status: "Pure equity-holding entity",
  entity_tax_residency: "Entity tax residency",
  income_type: "Income type",
  income_legal_character: "Legal character of the income",
  payer_entity: "Paying entity",
  dividend_amount: "Dividend amount",
  dividend_currency: "Dividend currency",
  accrual_date: "Accrual date",
  underlying_profit_period: "Underlying profit period",
  source_analysis: "Source of the income",
  receipt_location: "Where the income was received",
  receipt_date: "Receipt date",
  bank_or_account_path: "Bank account / funds path",
  set_off_or_clearing_arrangement: "Set-off or clearing arrangement",
  cash_pool_arrangement: "Cash-pool arrangement",
  payment_on_behalf_arrangement: "Payment-on-behalf arrangement",
  direct_or_indirect_holding: "Direct or indirect holding",
  investee_entity: "Investee entity",
  holding_percentage_pct: "Shareholding (%)",
  continuous_holding_period_months: "Continuous holding period (months)",
  acquisition_date: "Share acquisition date",
  beneficial_owner_status: "Beneficial owner",
  foreign_tax_on_dividend_or_underlying_profit: "Foreign tax on the dividend or underlying profit",
  foreign_nominal_tax_rate_pct: "Foreign headline tax rate (%)",
  foreign_tax_jurisdiction: "Foreign tax jurisdiction",
  underlying_tax_deductible_status: "Deductible at the payer (anti-hybrid)",
  foreign_tax_credit_available: "Foreign tax credit available",
  entity_activity_profile: "Core income-generating activities in HK",
  hk_adequate_employees: "Adequate qualified employees in HK",
  hk_adequate_premises: "Adequate premises in HK",
  hk_operating_expenditure_amount: "Operating expenditure in HK",
  hk_operating_expenditure_currency: "Operating expenditure currency",
  strategic_decision_making_location: "Where strategic decisions are made",
  outsourcing_and_supervision: "Outsourcing and HK supervision",
  hybrid_mismatch_arrangement: "Hybrid mismatch arrangement",
  main_purpose_tax_benefit_flag: "Main purpose is a tax benefit",
  restructuring_near_income_date: "Restructuring near the income date",
  commercial_rationale: "Commercial rationale",
  evidence_inventory: "Evidence inventory",
  expert_decision_status: "Expert review status",
};

export const NODE_INFO: Record<string, { label: string; statute: string }> = {
  scope: { label: "Covered taxpayer and income", statute: "s.15H" },
  income_characterisation: { label: "Foreign-sourced dividend", statute: "s.15H / s.15I" },
  receipt: { label: "Received in Hong Kong", statute: "s.15I" },
  financial_entity_exclusion: { label: "Regulated financial entity exclusion", statute: "s.15H" },
  economic_substance: { label: "Economic substance exception", statute: "s.15K" },
  participation_basic: { label: "Participation exception: thresholds", statute: "s.15M(2)" },
  foreign_tax_switchover: { label: "Subject-to-tax and switch-over", statute: "s.15N(2),(5),(7)" },
  anti_hybrid: { label: "Anti-hybrid mismatch", statute: "s.15N(3)" },
  main_purpose: { label: "Main purpose test", statute: "s.15N(4)" },
  compliance_filing: { label: "Notification and record keeping", statute: "s.15J / s.15S" },
  human_gate: { label: "Professional validation gate", statute: "cross-cutting" },
};

export const OUTPUT_LABELS: Record<NodeOutput, string> = {
  satisfied: "Established",
  not_satisfied: "Not established",
  unknown: "Unknown",
  conflict: "Conflict",
  condition_not_demonstrated: "Condition not demonstrated",
  human_review_required: "Needs human review",
};

export const TERMINAL_COPY: Record<TerminalState, { title: string; summary: string; listTitle: string }> = {
  research_only_output: {
    title: "Research-only output",
    summary:
      "The chain stopped before any professional judgement was reached. Fill the evidence gaps below and run the case again. No tax conclusion is issued.",
    listTitle: "Evidence gaps",
  },
  human_review_required: {
    title: "Human review required",
    summary:
      "The chain reached questions a machine must not decide, such as foreign-tax qualification, main purpose or the adequacy of substance. A qualified adviser has to take it from here.",
    listTitle: "For a qualified adviser to decide",
  },
  stop_and_escalate: {
    title: "Stop and escalate",
    summary:
      "The facts contradict each other, so the analysis stopped. The conflict is recorded as a conflict, never silently turned into a no. Resolve it and confirm the fact card before running again.",
    listTitle: "Conflicting facts",
  },
};

export function fieldLabel(field: string): string {
  return FIELD_LABELS[field] ?? field.replace(/_/g, " ");
}

export function formatValue(value: FactRow["value"]): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return value.toLocaleString("en-US");
  if (typeof value === "boolean") return value ? "Yes" : "No";
  const known: Record<string, string> = {
    yes: "Yes",
    no: "No",
    not_applicable: "Not applicable",
    received_in_hk: "Received in Hong Kong",
    deemed_received_in_hk: "Deemed received in Hong Kong",
    received_outside_hk: "Received outside Hong Kong",
    candidate_foreign_dividend: "Candidate foreign-sourced dividend",
    not_foreign_dividend: "Not a foreign-sourced dividend",
    foreign_sourced: "Foreign-sourced",
    hk_sourced: "Hong Kong-sourced",
    direct: "Direct",
    indirect: "Indirect",
    both: "Direct and indirect",
    adequate: "Adequate",
    inadequate: "Inadequate",
    taxed: "Taxed",
    untaxed: "Untaxed",
    partially_taxed: "Partially taxed",
    pure_equity_holding: "Pure equity-holding",
    general_entity: "General entity",
    in_hk: "In Hong Kong",
    outside_hk: "Outside Hong Kong",
    mixed: "Mixed",
  };
  return known[value] ?? value.replace(/_/g, " ");
}
