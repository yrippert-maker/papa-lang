// PAPA Lang — Full Server Example
// Run: cargo run -- run examples/papa_server.pl

log.info("Starting PAPA server...")

// Setup database
db.sql("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, name TEXT, email TEXT, created_at TEXT)")
db.sql("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, user_id TEXT, token TEXT)")

log.info("Database tables created")

// Setup cache
cache.set("app:version", "0.1.0")
cache.set("app:name", "PAPA Ecosystem")

// Insert test data
db.insert("users", { id: "u1", name: "Admin", email: "admin@papa.dev", created_at: "2026-02-22" })
log.info("Test data inserted")

// Query
let users = db.query("users")
print("Users:", users)

// Cache check
let version = cache.get("app:version")
print("Version:", version)

// Crypto
let password_hash = crypto.hash("secret123")
print("Hash:", password_hash)
let valid = crypto.verify("secret123", password_hash)
print("Valid:", valid)

// Queue
queue.push("tasks", "process_user_1")
queue.push("tasks", "process_user_2")
let task = queue.pop("tasks")
print("Next task:", task)

// Log levels
log.info("Server ready")
log.warn("Running in development mode")

print("")
print("All engines working! ✅")
