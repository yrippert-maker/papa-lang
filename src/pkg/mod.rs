//! Package manifest (papa.toml) support.

use serde::Deserialize;
use std::collections::HashMap;
use std::path::Path;

#[derive(Debug, Deserialize, Default)]
pub struct PapaToml {
    pub package: Option<PackageInfo>,
    #[serde(default)]
    pub dependencies: HashMap<String, toml::Value>,
}

#[derive(Debug, Deserialize)]
pub struct PackageInfo {
    pub name: String,
    #[serde(default)]
    pub version: String,
    #[serde(default)]
    pub description: String,
}

/// Load and parse papa.toml from the given directory (or current dir if None).
pub fn load_papa_toml(dir: Option<&Path>) -> Result<Option<PapaToml>, toml::de::Error> {
    let path = dir
        .map(|d| d.join("papa.toml"))
        .unwrap_or_else(|| std::path::PathBuf::from("papa.toml"));
    if path.exists() {
        let s = std::fs::read_to_string(&path).unwrap_or_default();
        let p: PapaToml = toml::from_str(&s)?;
        Ok(Some(p))
    } else {
        Ok(None)
    }
}
