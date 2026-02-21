//! Secrets from env and local store.

use dashmap::DashMap;
use std::env;

pub struct SecretsEngine {
    secrets: DashMap<String, String>,
}

impl SecretsEngine {
    pub fn new() -> Self {
        Self {
            secrets: DashMap::new(),
        }
    }

    pub fn get(&self, key: &str) -> Option<String> {
        self.secrets
            .get(key)
            .map(|v| v.clone())
            .or_else(|| env::var(key).ok())
    }

    pub fn set(&self, key: &str, value: &str) {
        self.secrets.insert(key.to_string(), value.to_string());
    }
}
