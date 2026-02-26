/** Swarm agent types */

export interface AgentConfig {
  name: string;
  model: string;
  guard: string;
  hrsThreshold: number;
  memoryEnabled?: boolean;
}

export interface SwarmConfig {
  name: string;
  agents: AgentConfig[];
  consensus?: { required: number; of: number };
  anchor?: string;
  piiFilter?: boolean;
  hrsMax?: number;
}

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
