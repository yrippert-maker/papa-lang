export type { Verdict, HRSScore, OrchestrateMode } from "./hrs";
export type { SwarmConfig, AgentConfig, SwarmResult, AgentResult } from "./swarm";
export type { GuardResult, PIIMatch, InjectionSignal } from "./guard";

export interface OrchestrateResult {
  response: string;
  agent_used: string;
  hrs: number;
  verdict: string;
  flagged_claims: string[];
  blocked: boolean;
  retried?: boolean;
  swarm_mode?: boolean;
  rag_context_used?: boolean;
  mode?: string;
}
