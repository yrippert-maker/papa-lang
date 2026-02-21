//! In-memory job queues.

use dashmap::DashMap;
use std::collections::VecDeque;

pub struct QueueEngine {
    queues: DashMap<String, VecDeque<String>>,
}

impl QueueEngine {
    pub fn new() -> Self {
        Self {
            queues: DashMap::new(),
        }
    }

    pub fn push(&self, queue: &str, data: &str) {
        self.queues
            .entry(queue.to_string())
            .or_insert(VecDeque::new())
            .push_back(data.to_string());
    }

    pub fn pop(&self, queue: &str) -> Option<String> {
        self.queues.get_mut(queue)?.pop_front()
    }

    pub fn len(&self, queue: &str) -> usize {
        self.queues.get(queue).map(|q| q.len()).unwrap_or(0)
    }
}
