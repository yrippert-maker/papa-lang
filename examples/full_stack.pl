// full_stack.pl — Full stack PAPA Lang demo
// Shows: DB + Cache + HTTP + AI working together

print("=== PAPA Lang Full Stack Demo ===")
print("")

// 1. Database
print("▸ Setting up database...")
db.sql("CREATE TABLE IF NOT EXISTS visitors (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, visited_at TEXT)")
db.sql("INSERT INTO visitors (name, visited_at) VALUES ('PAPA', datetime('now'))")
let visitors = db.query("visitors")
print("  Visitors in DB: " + visitors)
print("")

// 2. Cache
print("▸ Setting up cache...")
cache.set("app:name", "PAPA Ecosystem")
cache.set("app:version", "0.1.0")
let app_name = cache.get("app:name")
print("  Cached app name: " + app_name)
print("")

// 3. Queue
print("▸ Testing queue...")
queue.push("tasks", "send_welcome_email")
queue.push("tasks", "generate_report")
let task = queue.pop("tasks")
print("  Next task: " + task)
print("")

// 4. Logging
log.info("Full stack demo starting")
log.info("Database ready, cache ready, queue ready")

// 5. Crypto
let hashed = crypto.hash("admin-password")
print("▸ Password hashed: " + hashed)
let valid = crypto.verify("admin-password", hashed)
print("  Verify correct password: " + valid)
print("")

// 6. HTTP Server (will block)
print("▸ Starting HTTP server...")
print("  All engines active: DB ✅ Cache ✅ Queue ✅ Log ✅ Crypto ✅")
print("")

server app {
    port: 8080
}

route GET "/health" {
    { status: "ok", engines: "all_active" }
}

route GET "/api/visitors" {
    { visitors: "query_db_here" }
}

app.start()
