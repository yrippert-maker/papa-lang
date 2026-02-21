//! File-based object storage.

use std::fs;
use std::path::PathBuf;

pub struct StorageEngine {
    base_path: PathBuf,
}

impl StorageEngine {
    pub fn new() -> Self {
        let path = PathBuf::from("./papa_storage");
        fs::create_dir_all(&path).ok();
        Self { base_path: path }
    }

    pub fn put(&self, key: &str, data: &[u8]) -> Result<(), String> {
        let path = self.base_path.join(key);
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }
        fs::write(&path, data).map_err(|e| e.to_string())
    }

    pub fn get(&self, key: &str) -> Result<Vec<u8>, String> {
        let path = self.base_path.join(key);
        fs::read(&path).map_err(|e| e.to_string())
    }

    pub fn delete(&self, key: &str) -> Result<(), String> {
        let path = self.base_path.join(key);
        fs::remove_file(&path).map_err(|e| e.to_string())
    }
}
