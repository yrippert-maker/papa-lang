//! In-memory cache engine with TTL.

use dashmap::DashMap;
use std::time::{Duration, Instant};

struct CacheEntry {
    value: String,
    expires_at: Option<Instant>,
}

pub struct CacheEngine {
    store: DashMap<String, CacheEntry>,
}

impl CacheEngine {
    pub fn new() -> Self {
        Self {
            store: DashMap::new(),
        }
    }

    pub fn set(&self, key: &str, value: &str, ttl_secs: Option<u64>) -> Result<(), String> {
        let expires_at = ttl_secs.map(|t| Instant::now() + Duration::from_secs(t));
        self.store.insert(
            key.to_string(),
            CacheEntry {
                value: value.to_string(),
                expires_at,
            },
        );
        Ok(())
    }

    pub fn get(&self, key: &str) -> Option<String> {
        if let Some(entry) = self.store.get(key) {
            if let Some(exp) = entry.expires_at {
                if Instant::now() > exp {
                    drop(entry);
                    self.store.remove(key);
                    return None;
                }
            }
            Some(entry.value.clone())
        } else {
            None
        }
    }

    pub fn delete(&self, key: &str) -> bool {
        self.store.remove(key).is_some()
    }

    pub fn keys(&self, pattern: &str) -> Vec<String> {
        let prefix = pattern.trim_end_matches('*');
        self.store
            .iter()
            .filter(|e| e.key().starts_with(prefix))
            .map(|e| e.key().clone())
            .collect()
    }
}
