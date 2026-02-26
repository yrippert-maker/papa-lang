/** PapaClient — HTTP client for papa-app orchestrate and RAG */

import type { OrchestrateResult } from "../types";

export interface OrchestrateOptions {
  mode?: "auto" | "single" | "swarm" | "tool";
  session_id?: string;
  skip_validation?: boolean;
}

export interface RAGResult {
  chunks: Array<{ content: string; score: number }>;
  context: string;
}

export class PapaClient {
  constructor(
    private baseUrl: string,
    private apiKey?: string
  ) {}

  async orchestrate(
    query: string,
    options?: OrchestrateOptions
  ): Promise<OrchestrateResult> {
    const res = await fetch(`${this.baseUrl}/api/v1/ai/orchestrate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(this.apiKey && { Authorization: `Bearer ${this.apiKey}` }),
      },
      body: JSON.stringify({
        prompt: query,
        force_single: options?.mode === "single",
        skip_validation: options?.skip_validation ?? false,
      }),
    });

    if (!res.ok) {
      throw new Error(`papa-app error: ${res.status}`);
    }
    return res.json();
  }

  async ragSearch(query: string, topK = 5): Promise<RAGResult> {
    const res = await fetch(
      `${this.baseUrl}/api/v1/rag/search?q=${encodeURIComponent(query)}&top_k=${topK}`,
      {
        headers: this.apiKey ? { Authorization: `Bearer ${this.apiKey}` } : {},
      }
    );
    if (!res.ok) {
      throw new Error(`RAG error: ${res.status}`);
    }
    const data = await res.json();
    return {
      chunks: data.chunks || [],
      context: data.context || "",
    };
  }
}
