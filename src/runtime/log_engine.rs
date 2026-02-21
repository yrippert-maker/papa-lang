//! Structured logging engine.

use chrono::Utc;
use std::sync::Mutex;

pub struct LogEntry {
    pub level: String,
    pub message: String,
    pub timestamp: String,
}

pub struct LogEngine {
    entries: Mutex<Vec<LogEntry>>,
}

impl LogEngine {
    pub fn new() -> Self {
        Self {
            entries: Mutex::new(Vec::new()),
        }
    }

    pub fn log(&self, level: &str, message: &str) {
        let entry = LogEntry {
            level: level.to_string(),
            message: message.to_string(),
            timestamp: Utc::now().to_rfc3339(),
        };

        let prefix = match level {
            "error" => "\x1b[31m[ERROR]\x1b[0m",
            "warn" => "\x1b[33m[WARN]\x1b[0m",
            "info" => "\x1b[32m[INFO]\x1b[0m",
            "debug" => "\x1b[36m[DEBUG]\x1b[0m",
            _ => "[LOG]",
        };
        println!("{} {} {}", prefix, entry.timestamp, message);

        if let Ok(mut entries) = self.entries.lock() {
            entries.push(entry);
            if entries.len() > 10000 {
                entries.drain(0..5000);
            }
        }
    }
}
