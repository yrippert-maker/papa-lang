//! Built-in SQLite database engine.

use rusqlite::{params, params_from_iter, Connection};
use serde_json::Value as JsonValue;
use std::sync::Mutex;

pub struct DbEngine {
    conn: Mutex<Connection>,
}

impl DbEngine {
    pub fn new() -> Self {
        let conn = Connection::open_in_memory()
            .expect("Failed to create in-memory database");
        conn.execute_batch("PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;")
            .expect("Failed to set pragmas");
        Self {
            conn: Mutex::new(conn),
        }
    }

    pub fn execute(&self, sql: &str) -> Result<usize, String> {
        let conn = self.conn.lock().map_err(|e| e.to_string())?;
        conn.execute(sql, []).map_err(|e| e.to_string())
    }

    pub fn query(&self, sql: &str) -> Result<Vec<JsonValue>, String> {
        let conn = self.conn.lock().map_err(|e| e.to_string())?;
        let mut stmt = conn.prepare(sql).map_err(|e| e.to_string())?;
        let column_names: Vec<String> = stmt
            .column_names()
            .iter()
            .map(|c| c.to_string())
            .collect();

        let rows = stmt
            .query_map([], |row| {
                let mut map = serde_json::Map::new();
                for (i, name) in column_names.iter().enumerate() {
                    let val: rusqlite::types::Value = row.get(i)?;
                    let json_val = match val {
                        rusqlite::types::Value::Null => JsonValue::Null,
                        rusqlite::types::Value::Integer(n) => JsonValue::Number(serde_json::Number::from(n)),
                        rusqlite::types::Value::Real(f) => serde_json::Number::from_f64(f)
                            .map(JsonValue::Number)
                            .unwrap_or(JsonValue::Null),
                        rusqlite::types::Value::Text(s) => JsonValue::String(s),
                        rusqlite::types::Value::Blob(b) => {
                            JsonValue::String(base64::Engine::encode(&base64::engine::general_purpose::STANDARD, &b))
                        }
                    };
                    map.insert(name.clone(), json_val);
                }
                Ok(JsonValue::Object(map))
            })
            .map_err(|e| e.to_string())?;

        rows.collect::<Result<Vec<_>, _>>().map_err(|e| e.to_string())
    }

    pub fn insert(&self, table: &str, data: &JsonValue) -> Result<JsonValue, String> {
        if let JsonValue::Object(map) = data {
            let columns: Vec<&String> = map.keys().collect();
            let placeholders: Vec<String> = (0..columns.len())
                .map(|i| format!("?{}", i + 1))
                .collect();

            let sql = format!(
                "INSERT INTO {} ({}) VALUES ({})",
                table,
                columns.iter().map(|c| c.as_str()).collect::<Vec<_>>().join(", "),
                placeholders.join(", ")
            );

            let conn = self.conn.lock().map_err(|e| e.to_string())?;

            let mut params: Vec<rusqlite::types::Value> = Vec::new();
            for v in map.values() {
                params.push(match v {
                    JsonValue::String(s) => rusqlite::types::Value::Text(s.clone()),
                    JsonValue::Number(n) => {
                        if let Some(i) = n.as_i64() {
                            rusqlite::types::Value::Integer(i)
                        } else {
                            rusqlite::types::Value::Real(n.as_f64().unwrap_or(0.0))
                        }
                    }
                    JsonValue::Bool(b) => rusqlite::types::Value::Integer(if *b { 1 } else { 0 }),
                    JsonValue::Null => rusqlite::types::Value::Null,
                    _ => rusqlite::types::Value::Text(v.to_string()),
                });
            }

            conn.execute(&sql, params_from_iter(params.iter()))
                .map_err(|e| e.to_string())?;

            let id = conn.last_insert_rowid();
            let mut result = map.clone();
            result.insert(
                "_rowid".to_string(),
                JsonValue::Number(serde_json::Number::from(id)),
            );
            Ok(JsonValue::Object(result))
        } else {
            Err("insert() requires a map/object".into())
        }
    }

    pub fn find(&self, table: &str, id_col: &str, id_val: &str) -> Result<Option<JsonValue>, String> {
        let sql = format!("SELECT * FROM {} WHERE {} = ?1 LIMIT 1", table, id_col);
        let conn = self.conn.lock().map_err(|e| e.to_string())?;
        let mut stmt = conn.prepare(&sql).map_err(|e| e.to_string())?;
        let column_names: Vec<String> = stmt.column_names().iter().map(|c| c.to_string()).collect();

        let mut rows = stmt.query([id_val]).map_err(|e| e.to_string())?;
        let opt_row = rows.next().map_err(|e| e.to_string())?;
        let Some(row) = opt_row else {
            return Ok(None);
        };
        let mut map = serde_json::Map::new();
        for (i, name) in column_names.iter().enumerate() {
            let val: rusqlite::types::Value = row.get(i).map_err(|e: rusqlite::Error| e.to_string())?;
            let json_val = match val {
                rusqlite::types::Value::Null => JsonValue::Null,
                rusqlite::types::Value::Integer(n) => JsonValue::Number(serde_json::Number::from(n)),
                rusqlite::types::Value::Real(f) => serde_json::Number::from_f64(f)
                    .map(JsonValue::Number)
                    .unwrap_or(JsonValue::Null),
                rusqlite::types::Value::Text(s) => JsonValue::String(s),
                rusqlite::types::Value::Blob(b) => JsonValue::String(
                    base64::Engine::encode(&base64::engine::general_purpose::STANDARD, &b),
                ),
            };
            map.insert(name.clone(), json_val);
        }
        Ok(Some(JsonValue::Object(map)))
    }

    pub fn delete(&self, table: &str, id_col: &str, id_val: &str) -> Result<usize, String> {
        let sql = format!("DELETE FROM {} WHERE {} = ?1", table, id_col);
        let conn = self.conn.lock().map_err(|e| e.to_string())?;
        conn.execute(&sql, params![id_val]).map_err(|e| e.to_string())
    }
}
