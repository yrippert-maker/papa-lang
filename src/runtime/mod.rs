//! PAPA Lang runtime engines — built-in db, cache, http, ai, etc.

pub mod db_engine;
pub mod cache_engine;
pub mod http_engine;
pub mod ai_engine;
pub mod queue_engine;
pub mod storage_engine;
pub mod secrets_engine;
pub mod metrics_engine;
pub mod log_engine;
pub mod crypto_engine;

use std::sync::{Arc, RwLock};

/// Global runtime state shared across all engines
pub struct PapaRuntime {
    pub db: db_engine::DbEngine,
    pub cache: cache_engine::CacheEngine,
    pub http: std::sync::RwLock<http_engine::HttpEngine>,
    pub ai: ai_engine::AiEngine,
    pub metrics: metrics_engine::MetricsEngine,
    pub logs: log_engine::LogEngine,
    pub secrets: secrets_engine::SecretsEngine,
    pub storage: storage_engine::StorageEngine,
    pub queue: queue_engine::QueueEngine,
}

impl PapaRuntime {
    pub fn new() -> Self {
        Self {
            db: db_engine::DbEngine::new(),
            cache: cache_engine::CacheEngine::new(),
            http: std::sync::RwLock::new(http_engine::HttpEngine::new()),
            ai: ai_engine::AiEngine::new(),
            metrics: metrics_engine::MetricsEngine::new(),
            logs: log_engine::LogEngine::new(),
            secrets: secrets_engine::SecretsEngine::new(),
            storage: storage_engine::StorageEngine::new(),
            queue: queue_engine::QueueEngine::new(),
        }
    }
}

lazy_static::lazy_static! {
    pub static ref RUNTIME: Arc<RwLock<PapaRuntime>> =
        Arc::new(RwLock::new(PapaRuntime::new()));
}
