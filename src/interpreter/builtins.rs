//! Built-in function implementations for runtime engines.

use super::value::Value;
use crate::runtime;
use serde_json::Value as JsonValue;

pub fn register_all(env: &mut crate::interpreter::evaluator::Environment) {
    // Core
    env.define("print", Value::Builtin("print".into()));
    env.define("type", Value::Builtin("type".into()));
    env.define("ok", Value::Builtin("ok".into()));
    env.define("err", Value::Builtin("err".into()));
    env.define("len", Value::Builtin("len".into()));
    env.define("uuid", Value::Builtin("uuid".into()));

    // DB
    env.define("db.sql", Value::Builtin("db.sql".into()));
    env.define("db.insert", Value::Builtin("db.insert".into()));
    env.define("db.find", Value::Builtin("db.find".into()));
    env.define("db.query", Value::Builtin("db.query".into()));
    env.define("db.delete", Value::Builtin("db.delete".into()));

    // Cache
    env.define("cache.set", Value::Builtin("cache.set".into()));
    env.define("cache.get", Value::Builtin("cache.get".into()));
    env.define("cache.delete", Value::Builtin("cache.delete".into()));
    env.define("cache.keys", Value::Builtin("cache.keys".into()));

    // Log
    env.define("log.info", Value::Builtin("log.info".into()));
    env.define("log.error", Value::Builtin("log.error".into()));
    env.define("log.warn", Value::Builtin("log.warn".into()));
    env.define("log.debug", Value::Builtin("log.debug".into()));

    // Crypto
    env.define("crypto.hash", Value::Builtin("crypto.hash".into()));
    env.define("crypto.verify", Value::Builtin("crypto.verify".into()));

    // Queue
    env.define("queue.push", Value::Builtin("queue.push".into()));
    env.define("queue.pop", Value::Builtin("queue.pop".into()));

    // Secrets
    env.define("secret", Value::Builtin("secret".into()));

    // AI
    env.define("ai.ask", Value::Builtin("ai.ask".into()));
    env.define("ai.models", Value::Builtin("ai.models".into()));

    // HTTP (app.start starts the server)
    env.define("app.start", Value::Builtin("app.start".into()));
}

pub fn call(name: &str, args: &[Value]) -> Result<Value, String> {
    match name {
        "print" => {
            let output: Vec<String> = args.iter().map(|a| a.to_string()).collect();
            println!("{}", output.join(" "));
            Ok(Value::None)
        }
        "type" => {
            if let Some(v) = args.first() {
                Ok(Value::Str(v.type_name().to_string()))
            } else {
                Err("type() requires 1 argument".into())
            }
        }
        "len" => match args.first() {
            Some(Value::Str(s)) => Ok(Value::Int(s.len() as i64)),
            Some(Value::List(l)) => Ok(Value::Int(l.len() as i64)),
            Some(Value::Map(m)) => Ok(Value::Int(m.len() as i64)),
            _ => Err("len() requires string, list, or map".into()),
        },
        "uuid" => Ok(Value::Str(uuid::Uuid::new_v4().to_string())),
        "ok" => {
            let v = args.first().cloned().unwrap_or(Value::None);
            Ok(Value::Ok(Box::new(v)))
        }
        "err" => {
            let v = args.first().cloned().unwrap_or(Value::None);
            Ok(Value::Err(Box::new(v)))
        }

        // DB
        "db.sql" => {
            let sql = args.first().and_then(Value::as_str).ok_or("db.sql requires SQL string")?;
            let rt = runtime::RUNTIME.read().map_err(|e| e.to_string())?;
            rt.db.execute(sql)?;
            Ok(Value::None)
        }
        "db.insert" => {
            let table = args.get(0).and_then(Value::as_str).ok_or("db.insert: need table")?;
            let data = args.get(1).map(|v| v.to_json()).ok_or("db.insert: need data")?;
            let rt = runtime::RUNTIME.read().map_err(|e| e.to_string())?;
            let result = rt.db.insert(table, &data)?;
            Ok(Value::from_json(result))
        }
        "db.find" => {
            let table = args.get(0).and_then(Value::as_str).ok_or("db.find: need table")?;
            let id = args.get(1).map(|v| v.to_string()).ok_or("db.find: need id")?;
            let rt = runtime::RUNTIME.read().map_err(|e| e.to_string())?;
            match rt.db.find(table, "id", &id)? {
                Some(row) => Ok(Value::from_json(row)),
                None => Ok(Value::None),
            }
        }
        "db.query" => {
            let table = args.get(0).and_then(Value::as_str).ok_or("db.query: need table")?;
            let sql = format!("SELECT * FROM {}", table);
            let rt = runtime::RUNTIME.read().map_err(|e| e.to_string())?;
            let results = rt.db.query(&sql)?;
            Ok(Value::from_json(JsonValue::Array(results)))
        }
        "db.delete" => {
            let table = args.get(0).and_then(Value::as_str).ok_or("db.delete: need table")?;
            let id = args.get(1).map(|v| v.to_string()).ok_or("db.delete: need id")?;
            let rt = runtime::RUNTIME.read().map_err(|e| e.to_string())?;
            let count = rt.db.delete(table, "id", &id)?;
            Ok(Value::Int(count as i64))
        }

        // Cache
        "cache.set" => {
            let key = args.get(0).and_then(Value::as_str).ok_or("cache.set: need key")?;
            let value = args.get(1).map(|v| v.to_json_string()).unwrap_or_else(|| "null".into());
            let ttl = args.get(2).and_then(|v| v.as_int()).map(|n| n as u64);
            let rt = runtime::RUNTIME.read().map_err(|e| e.to_string())?;
            rt.cache.set(key, &value, ttl)?;
            Ok(Value::Bool(true))
        }
        "cache.get" => {
            let key = args.get(0).and_then(Value::as_str).ok_or("cache.get: need key")?;
            let rt = runtime::RUNTIME.read().map_err(|e| e.to_string())?;
            match rt.cache.get(key) {
                Some(val) => Ok(serde_json::from_str(&val)
                    .map(Value::from_json)
                    .unwrap_or(Value::Str(val))),
                None => Ok(Value::None),
            }
        }
        "cache.delete" => {
            let key = args.get(0).and_then(Value::as_str).ok_or("cache.delete: need key")?;
            let rt = runtime::RUNTIME.read().map_err(|e| e.to_string())?;
            Ok(Value::Bool(rt.cache.delete(key)))
        }
        "cache.keys" => {
            let pattern = args.get(0).map(|v| v.to_string()).unwrap_or_else(|| "*".into());
            let rt = runtime::RUNTIME.read().map_err(|e| e.to_string())?;
            let keys = rt.cache.keys(&pattern);
            Ok(Value::List(keys.into_iter().map(Value::Str).collect()))
        }

        // Log
        "log.info" => {
            let msg = args.get(0).map(|v| v.to_string()).unwrap_or_default();
            let rt = runtime::RUNTIME.read().map_err(|e| e.to_string())?;
            rt.logs.log("info", &msg);
            Ok(Value::None)
        }
        "log.error" => {
            let msg = args.get(0).map(|v| v.to_string()).unwrap_or_default();
            let rt = runtime::RUNTIME.read().map_err(|e| e.to_string())?;
            rt.logs.log("error", &msg);
            Ok(Value::None)
        }
        "log.warn" => {
            let msg = args.get(0).map(|v| v.to_string()).unwrap_or_default();
            let rt = runtime::RUNTIME.read().map_err(|e| e.to_string())?;
            rt.logs.log("warn", &msg);
            Ok(Value::None)
        }
        "log.debug" => {
            let msg = args.get(0).map(|v| v.to_string()).unwrap_or_default();
            let rt = runtime::RUNTIME.read().map_err(|e| e.to_string())?;
            rt.logs.log("debug", &msg);
            Ok(Value::None)
        }

        // Crypto
        "crypto.hash" => {
            let input = args.get(0).and_then(Value::as_str).ok_or("crypto.hash: need input")?;
            let hash = bcrypt::hash(input, bcrypt::DEFAULT_COST).map_err(|e| e.to_string())?;
            Ok(Value::Str(hash))
        }
        "crypto.verify" => {
            let input = args.get(0).and_then(Value::as_str).ok_or("crypto.verify: need input")?;
            let hash = args.get(1).and_then(Value::as_str).ok_or("crypto.verify: need hash")?;
            let valid = bcrypt::verify(input, hash).map_err(|e| e.to_string())?;
            Ok(Value::Bool(valid))
        }

        // Queue
        "queue.push" => {
            let queue = args.get(0).and_then(Value::as_str).ok_or("queue.push: need queue")?;
            let data = args.get(1).map(|v| v.to_string()).unwrap_or_default();
            let rt = runtime::RUNTIME.read().map_err(|e| e.to_string())?;
            rt.queue.push(queue, &data);
            Ok(Value::None)
        }
        "queue.pop" => {
            let queue = args.get(0).and_then(Value::as_str).ok_or("queue.pop: need queue")?;
            let rt = runtime::RUNTIME.read().map_err(|e| e.to_string())?;
            match rt.queue.pop(queue) {
                Some(s) => Ok(Value::Str(s)),
                None => Ok(Value::None),
            }
        }

        // Secrets
        "secret" => {
            let key = args.get(0).and_then(Value::as_str).ok_or("secret: need key")?;
            let rt = runtime::RUNTIME.read().map_err(|e| e.to_string())?;
            match rt.secrets.get(key) {
                Some(val) => Ok(Value::Str(val)),
                None => Err(format!("Secret '{}' not found", key)),
            }
        }

        // AI
        "ai.ask" => {
            let prompt = args
                .get(0)
                .and_then(Value::as_str)
                .ok_or("ai.ask: need prompt string")?;
            let model = args.get(1).and_then(Value::as_str);
            let rt = runtime::RUNTIME.read().map_err(|e| e.to_string())?;
            let ai = &rt.ai;
            let rt_tokio = tokio::runtime::Runtime::new()
                .map_err(|e| format!("Failed to create runtime: {}", e))?;
            let result = rt_tokio.block_on(ai.ask(prompt, model, None, None));
            match result {
                Ok(s) => Ok(Value::Str(s)),
                Err(e) => Err(format!("ai.ask failed: {}", e)),
            }
        }
        "ai.models" => {
            let rt = runtime::RUNTIME.read().map_err(|e| e.to_string())?;
            let providers = rt.ai.list_providers();
            let default = rt
                .ai
                .default_model()
                .unwrap_or_else(|| "none".to_string());
            Ok(Value::Str(format!(
                "Providers: {:?}, Default: {}",
                providers, default
            )))
        }

        // HTTP
        "app.start" => {
            let rt = runtime::RUNTIME.read().map_err(|e| e.to_string())?;
            let http = rt.http.read().map_err(|e| e.to_string())?.clone();
            drop(rt);
            let rt_tokio = tokio::runtime::Runtime::new()
                .map_err(|e| format!("Failed to create runtime: {}", e))?;
            rt_tokio.block_on(http.start()).map_err(|e| format!("Server failed: {}", e))?;
            Ok(Value::None)
        }

        _ => Err(format!("Unknown builtin: {}", name)),
    }
}
