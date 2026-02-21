// api_server.pl — Real HTTP server in PAPA Lang
// Usage: pl run examples/api_server.pl
// Test:  curl http://localhost:8080/health
//        curl http://localhost:8080/api/hello

print("=== PAPA Lang HTTP Server ===")

server app {
    port: 8080
}

route GET "/health" {
    { status: "ok", server: "PAPA Lang", version: "0.1.0" }
}

route GET "/api/hello" {
    { message: "Hello from PAPA Lang!", timestamp: "2026-02-22" }
}

route GET "/api/info" {
    {
        name: "PAPA Ecosystem",
        language: "PAPA Lang",
        engines: ["db", "cache", "http", "ai", "log", "crypto", "queue", "secrets", "metrics", "storage"],
        status: "running"
    }
}

route POST "/api/echo" {
    { echo: "received", note: "POST body handling coming soon" }
}

app.start()
