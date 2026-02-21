//! Counters and gauges.

use dashmap::DashMap;
use std::sync::atomic::{AtomicU64, Ordering};

pub struct MetricsEngine {
    counters: DashMap<String, AtomicU64>,
}

impl MetricsEngine {
    pub fn new() -> Self {
        Self {
            counters: DashMap::new(),
        }
    }

    pub fn increment(&self, name: &str, value: u64) {
        self.counters
            .entry(name.to_string())
            .or_insert(AtomicU64::new(0))
            .fetch_add(value, Ordering::Relaxed);
    }

    pub fn get_counter(&self, name: &str) -> u64 {
        self.counters
            .get(name)
            .map(|c| c.load(Ordering::Relaxed))
            .unwrap_or(0)
    }
}
