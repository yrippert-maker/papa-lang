/** Guard (PII, injection) types */

export interface PIIMatch {
  type: string;
  value: string;
  position: number;
}

export interface InjectionSignal {
  pattern: string;
  severity: "HIGH" | "MEDIUM";
}

export interface GuardResult {
  sanitized_text: string;
  pii_redacted_count: number;
  blocked: boolean;
  block_reason?: string;
  injection_detected: boolean;
}
