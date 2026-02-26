/** Swarm agent types */

export interface AgentResult {
  agent: string;
  response: string;
  hrs_score?: number;
}

export interface SwarmResult {
  response: string;
  consensus_score: number;
  agents_used: number;
  hrs: number;
  verdict: string;
  individual_results?: AgentResult[];
}
