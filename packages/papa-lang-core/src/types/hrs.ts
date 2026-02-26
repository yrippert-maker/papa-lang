/** HRS (Hallucination Risk Score) types */

export type Verdict = "PASS" | "WARN" | "BLOCK";

export interface HRSScore {
  hrs: number;
  verdict: Verdict;
  flagged_claims: string[];
  mode?: string;
  latency_ms?: number;
}

export type OrchestrateMode = "auto" | "single" | "swarm" | "tool";
