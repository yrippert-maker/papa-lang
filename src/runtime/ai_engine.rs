//! Multi-provider AI engine — real HTTP calls to OpenAI, Anthropic, Google, xAI.

use reqwest::Client;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value as JsonValue};
use std::collections::HashMap;
use std::env;

/// Multi-provider AI engine for PAPA Lang
pub struct AiEngine {
    client: Client,
    providers: HashMap<String, ProviderConfig>,
    default_model: Option<String>,
}

#[derive(Clone, Debug)]
pub struct ProviderConfig {
    pub provider_type: ProviderType,
    pub api_key: String,
    pub base_url: String,
}

#[derive(Clone, Debug, PartialEq)]
pub enum ProviderType {
    OpenAI,
    Anthropic,
    Google,
    XAI,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatMessage {
    pub role: String,
    pub content: String,
}

#[derive(Debug)]
pub struct AiResponse {
    pub content: String,
    pub model: String,
    pub tokens_in: u32,
    pub tokens_out: u32,
}

impl AiEngine {
    pub fn new() -> Self {
        let engine = AiEngine {
            client: Client::builder()
                .timeout(std::time::Duration::from_secs(120))
                .build()
                .unwrap_or_default(),
            providers: HashMap::new(),
            default_model: None,
        };
        let mut engine = engine;
        engine.auto_configure();
        engine
    }

    fn auto_configure(&mut self) {
        if let Ok(key) = env::var("OPENAI_API_KEY") {
            if !key.is_empty() && !key.contains("...") {
                self.providers.insert(
                    "openai".to_string(),
                    ProviderConfig {
                        provider_type: ProviderType::OpenAI,
                        api_key: key,
                        base_url: env::var("OPENAI_BASE_URL")
                            .unwrap_or_else(|_| "https://api.openai.com".to_string()),
                    },
                );
                if self.default_model.is_none() {
                    self.default_model = Some("openai/gpt-4o-mini".to_string());
                }
            }
        }

        if let Ok(key) = env::var("ANTHROPIC_API_KEY") {
            if !key.is_empty() && !key.contains("...") {
                self.providers.insert(
                    "anthropic".to_string(),
                    ProviderConfig {
                        provider_type: ProviderType::Anthropic,
                        api_key: key,
                        base_url: env::var("ANTHROPIC_BASE_URL")
                            .unwrap_or_else(|_| "https://api.anthropic.com".to_string()),
                    },
                );
                if self.default_model.is_none() {
                    self.default_model =
                        Some("anthropic/claude-sonnet-4-20250514".to_string());
                }
            }
        }

        if let Ok(key) = env::var("GOOGLE_API_KEY") {
            if !key.is_empty() && !key.contains("...") {
                self.providers.insert(
                    "google".to_string(),
                    ProviderConfig {
                        provider_type: ProviderType::Google,
                        api_key: key,
                        base_url: "https://generativelanguage.googleapis.com".to_string(),
                    },
                );
                if self.default_model.is_none() {
                    self.default_model = Some("google/gemini-2.0-flash".to_string());
                }
            }
        }

        if let Ok(key) = env::var("XAI_API_KEY") {
            if !key.is_empty() && !key.contains("...") {
                self.providers.insert(
                    "xai".to_string(),
                    ProviderConfig {
                        provider_type: ProviderType::XAI,
                        api_key: key,
                        base_url: "https://api.x.ai".to_string(),
                    },
                );
            }
        }
    }

    pub fn add_provider(
        &mut self,
        name: &str,
        provider_type: ProviderType,
        api_key: &str,
        base_url: Option<&str>,
    ) {
        let default_url = match provider_type {
            ProviderType::OpenAI => "https://api.openai.com",
            ProviderType::Anthropic => "https://api.anthropic.com",
            ProviderType::Google => "https://generativelanguage.googleapis.com",
            ProviderType::XAI => "https://api.x.ai",
        };
        self.providers.insert(
            name.to_string(),
            ProviderConfig {
                provider_type,
                api_key: api_key.to_string(),
                base_url: base_url.unwrap_or(default_url).to_string(),
            },
        );
    }

    pub fn set_default_model(&mut self, model: &str) {
        self.default_model = Some(model.to_string());
    }

    fn parse_model_parts(&self, model: &str) -> (String, String) {
        if let Some((provider, name)) = model.split_once('/') {
            (provider.to_string(), name.to_string())
        } else if let Some(ref default) = self.default_model {
            if let Some((p, _)) = default.split_once('/') {
                return (p.to_string(), model.to_string());
            }
            ("openai".to_string(), model.to_string())
        } else {
            ("openai".to_string(), model.to_string())
        }
    }

    pub fn list_providers(&self) -> Vec<String> {
        self.providers.keys().cloned().collect()
    }

    pub fn default_model(&self) -> Option<String> {
        self.default_model.clone()
    }

    pub async fn ask(
        &self,
        prompt: &str,
        model: Option<&str>,
        temperature: Option<f64>,
        max_tokens: Option<u32>,
    ) -> Result<String, String> {
        let model_str = model
            .map(|s| s.to_string())
            .or_else(|| self.default_model.clone())
            .ok_or_else(|| {
                "No model specified. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY."
                    .to_string()
            })?;

        let messages = vec![ChatMessage {
            role: "user".to_string(),
            content: prompt.to_string(),
        }];

        let response = self
            .chat(&model_str, &messages, temperature, max_tokens)
            .await?;
        Ok(response.content)
    }

    pub async fn chat(
        &self,
        model: &str,
        messages: &[ChatMessage],
        temperature: Option<f64>,
        max_tokens: Option<u32>,
    ) -> Result<AiResponse, String> {
        let (provider_name, model_name) = self.parse_model_parts(model);

        let provider = self.providers.get(&provider_name).ok_or_else(|| {
            let available = self.list_providers().join(", ");
            format!(
                "Provider '{provider_name}' not configured. Available: [{}]",
                if available.is_empty() {
                    "none — set OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY"
                        .to_string()
                } else {
                    available
                }
            )
        })?;

        match provider.provider_type {
            ProviderType::OpenAI | ProviderType::XAI => {
                self.call_openai_compatible(
                    provider,
                    &model_name,
                    messages,
                    temperature,
                    max_tokens,
                )
                .await
            }
            ProviderType::Anthropic => {
                self.call_anthropic(provider, &model_name, messages, temperature, max_tokens)
                    .await
            }
            ProviderType::Google => {
                self.call_google(
                    provider,
                    &model_name,
                    messages,
                    temperature,
                    max_tokens,
                )
                .await
            }
        }
    }

    async fn call_openai_compatible(
        &self,
        provider: &ProviderConfig,
        model: &str,
        messages: &[ChatMessage],
        temperature: Option<f64>,
        max_tokens: Option<u32>,
    ) -> Result<AiResponse, String> {
        let url = format!("{}/v1/chat/completions", provider.base_url);

        let body = json!({
            "model": model,
            "messages": messages.iter().map(|m| json!({
                "role": m.role,
                "content": m.content,
            })).collect::<Vec<_>>(),
            "temperature": temperature.unwrap_or(0.7),
            "max_tokens": max_tokens.unwrap_or(4096),
        });

        let resp = self
            .client
            .post(&url)
            .header("Authorization", format!("Bearer {}", provider.api_key))
            .header("Content-Type", "application/json")
            .json(&body)
            .send()
            .await
            .map_err(|e| format!("HTTP request failed: {}", e))?;

        let status = resp.status();
        let resp_text = resp
            .text()
            .await
            .map_err(|e| format!("Failed to read response: {}", e))?;

        if !status.is_success() {
            return Err(format!(
                "OpenAI API error ({}): {}",
                status,
                truncate_str(&resp_text, 500)
            ));
        }

        let data: JsonValue = serde_json::from_str(&resp_text).map_err(|e| {
            format!(
                "Failed to parse JSON: {} — raw: {}",
                e,
                truncate_str(&resp_text, 200)
            )
        })?;

        let content = data["choices"][0]["message"]["content"]
            .as_str()
            .unwrap_or("")
            .to_string();

        Ok(AiResponse {
            content,
            model: model.to_string(),
            tokens_in: data["usage"]["prompt_tokens"].as_u64().unwrap_or(0) as u32,
            tokens_out: data["usage"]["completion_tokens"].as_u64().unwrap_or(0) as u32,
        })
    }

    async fn call_anthropic(
        &self,
        provider: &ProviderConfig,
        model: &str,
        messages: &[ChatMessage],
        temperature: Option<f64>,
        max_tokens: Option<u32>,
    ) -> Result<AiResponse, String> {
        let url = format!("{}/v1/messages", provider.base_url);

        let mut system_text = String::new();
        let mut api_messages = Vec::new();

        for msg in messages {
            if msg.role == "system" {
                system_text.push_str(&msg.content);
            } else {
                api_messages.push(json!({
                    "role": msg.role,
                    "content": msg.content,
                }));
            }
        }

        if api_messages.is_empty() {
            return Err("Anthropic requires at least one user message".to_string());
        }

        let mut body = json!({
            "model": model,
            "messages": api_messages,
            "max_tokens": max_tokens.unwrap_or(4096),
        });

        if !system_text.is_empty() {
            body["system"] = json!(system_text);
        }
        if let Some(temp) = temperature {
            body["temperature"] = json!(temp);
        }

        let resp = self
            .client
            .post(&url)
            .header("x-api-key", &provider.api_key)
            .header("anthropic-version", "2023-06-01")
            .header("Content-Type", "application/json")
            .json(&body)
            .send()
            .await
            .map_err(|e| format!("HTTP request failed: {}", e))?;

        let status = resp.status();
        let resp_text = resp
            .text()
            .await
            .map_err(|e| format!("Failed to read response: {}", e))?;

        if !status.is_success() {
            return Err(format!(
                "Anthropic API error ({}): {}",
                status,
                truncate_str(&resp_text, 500)
            ));
        }

        let data: JsonValue = serde_json::from_str(&resp_text).map_err(|e| {
            format!(
                "Failed to parse JSON: {} — raw: {}",
                e,
                truncate_str(&resp_text, 200)
            )
        })?;

        let content = data["content"]
            .as_array()
            .map(|blocks| {
                blocks
                    .iter()
                    .filter_map(|b| b["text"].as_str())
                    .collect::<Vec<_>>()
                    .join("")
            })
            .unwrap_or_default();

        Ok(AiResponse {
            content,
            model: model.to_string(),
            tokens_in: data["usage"]["input_tokens"].as_u64().unwrap_or(0) as u32,
            tokens_out: data["usage"]["output_tokens"].as_u64().unwrap_or(0) as u32,
        })
    }

    async fn call_google(
        &self,
        provider: &ProviderConfig,
        model: &str,
        messages: &[ChatMessage],
        temperature: Option<f64>,
        max_tokens: Option<u32>,
    ) -> Result<AiResponse, String> {
        let url = format!(
            "{}/v1beta/models/{}:generateContent?key={}",
            provider.base_url, model, provider.api_key
        );

        let mut system_instruction = String::new();
        let mut contents = Vec::new();

        for msg in messages {
            if msg.role == "system" {
                system_instruction.push_str(&msg.content);
            } else {
                let role = if msg.role == "assistant" {
                    "model"
                } else {
                    &msg.role
                };
                contents.push(json!({
                    "role": role,
                    "parts": [{ "text": msg.content }]
                }));
            }
        }

        if contents.is_empty() {
            return Err("Gemini requires at least one message".to_string());
        }

        let mut body = json!({
            "contents": contents,
            "generationConfig": {
                "temperature": temperature.unwrap_or(0.7),
                "maxOutputTokens": max_tokens.unwrap_or(4096),
            }
        });

        if !system_instruction.is_empty() {
            body["systemInstruction"] = json!({
                "parts": [{ "text": system_instruction }]
            });
        }

        let resp = self
            .client
            .post(&url)
            .header("Content-Type", "application/json")
            .json(&body)
            .send()
            .await
            .map_err(|e| format!("HTTP request failed: {}", e))?;

        let status = resp.status();
        let resp_text = resp
            .text()
            .await
            .map_err(|e| format!("Failed to read response: {}", e))?;

        if !status.is_success() {
            return Err(format!(
                "Gemini API error ({}): {}",
                status,
                truncate_str(&resp_text, 500)
            ));
        }

        let data: JsonValue = serde_json::from_str(&resp_text).map_err(|e| {
            format!(
                "Failed to parse JSON: {} — raw: {}",
                e,
                truncate_str(&resp_text, 200)
            )
        })?;

        let content = data["candidates"][0]["content"]["parts"][0]["text"]
            .as_str()
            .unwrap_or("")
            .to_string();

        Ok(AiResponse {
            content,
            model: model.to_string(),
            tokens_in: data["usageMetadata"]["promptTokenCount"]
                .as_u64()
                .unwrap_or(0) as u32,
            tokens_out: data["usageMetadata"]["candidatesTokenCount"]
                .as_u64()
                .unwrap_or(0) as u32,
        })
    }
}

fn truncate_str(s: &str, max: usize) -> String {
    if s.len() <= max {
        s.to_string()
    } else {
        format!("{}...", &s[..max])
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_model() {
        let engine = AiEngine::new();
        assert_eq!(
            engine.parse_model_parts("openai/gpt-4o"),
            ("openai".to_string(), "gpt-4o".to_string())
        );
        assert_eq!(
            engine.parse_model_parts("anthropic/claude-sonnet-4-20250514"),
            (
                "anthropic".to_string(),
                "claude-sonnet-4-20250514".to_string()
            )
        );
    }

    #[test]
    fn test_add_provider() {
        let mut engine = AiEngine::new();
        engine.add_provider(
            "test",
            ProviderType::OpenAI,
            "sk-test-key",
            None,
        );
        assert!(engine.list_providers().contains(&"test".to_string()));
    }

    /// Integration tests — require real API keys. Run with:
    /// OPENAI_API_KEY=sk-... cargo test -- --ignored
    #[tokio::test]
    #[ignore]
    async fn test_openai_real_call() {
        let engine = AiEngine::new();
        let result = engine
            .ask(
                "Say exactly: PAPA LANG WORKS",
                Some("openai/gpt-4o-mini"),
                Some(0.0),
                Some(50),
            )
            .await;
        assert!(result.is_ok(), "OpenAI call failed: {:?}", result.err());
        let text = result.unwrap();
        assert!(
            text.contains("PAPA") || text.contains("LANG"),
            "Unexpected response: {}",
            text
        );
    }

    #[tokio::test]
    #[ignore]
    async fn test_anthropic_real_call() {
        let engine = AiEngine::new();
        let result = engine
            .ask(
                "Say exactly: PAPA LANG WORKS",
                Some("anthropic/claude-sonnet-4-20250514"),
                Some(0.0),
                Some(50),
            )
            .await;
        assert!(result.is_ok(), "Anthropic call failed: {:?}", result.err());
    }

    #[tokio::test]
    #[ignore]
    async fn test_google_real_call() {
        let engine = AiEngine::new();
        let result = engine
            .ask(
                "Say exactly: PAPA LANG WORKS",
                Some("google/gemini-2.0-flash"),
                Some(0.0),
                Some(50),
            )
            .await;
        assert!(result.is_ok(), "Google call failed: {:?}", result.err());
    }
}
