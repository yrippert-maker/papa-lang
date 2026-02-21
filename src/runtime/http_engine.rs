//! HTTP server engine — real axum server with PL-defined routes.

use axum::{
    routing::{delete, get, post, put},
    Json,
};
use serde_json::Value as JsonValue;

/// Route handler — stores PL-defined response
#[derive(Clone, Debug)]
pub struct RouteHandler {
    pub method: String,
    pub path: String,
    pub response_body: JsonValue,
}

/// Server configuration from PL `server { }` block
#[derive(Clone, Debug)]
pub struct ServerConfig {
    pub port: u16,
    pub host: String,
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self {
            port: 8080,
            host: "0.0.0.0".to_string(),
        }
    }
}

#[derive(Clone)]
pub struct HttpEngine {
    pub config: ServerConfig,
    pub routes: Vec<RouteHandler>,
}

impl HttpEngine {
    pub fn new() -> Self {
        Self {
            config: ServerConfig::default(),
            routes: Vec::new(),
        }
    }

    pub fn set_config(&mut self, port: u16, host: &str) {
        self.config.port = port;
        self.config.host = host.to_string();
    }

    /// Register a route (called from PL `route GET "/path" { ... }`)
    pub fn add_route(&mut self, method: &str, path: &str, response: JsonValue) {
        self.routes.push(RouteHandler {
            method: method.to_uppercase(),
            path: path.to_string(),
            response_body: response,
        });
    }

    /// Start the HTTP server (blocking)
    pub async fn start(&self) -> Result<(), String> {
        let mut app = axum::Router::new();

        for route in &self.routes {
            let body = route.response_body.clone();
            let path = route.path.clone();

            match route.method.as_str() {
                "GET" => {
                    app = app.route(&path, get(move || async move { Json(body) }));
                }
                "POST" => {
                    app = app.route(&path, post(move || async move { Json(body) }));
                }
                "PUT" => {
                    app = app.route(&path, put(move || async move { Json(body) }));
                }
                "DELETE" => {
                    app = app.route(&path, delete(move || async move { Json(body) }));
                }
                _ => {
                    eprintln!(
                        "Warning: unsupported HTTP method '{}' for route '{}'",
                        route.method, route.path
                    );
                }
            }
        }

        // CORS
        let cors = tower_http::cors::CorsLayer::permissive();
        let app = app.layer(cors);

        let addr = format!("{}:{}", self.config.host, self.config.port);
        println!("🚀 PAPA Server running on http://{}", addr);
        println!("   Routes:");
        for route in &self.routes {
            println!("     {} {}", route.method, route.path);
        }
        println!();
        println!("   Press Ctrl+C to stop.");

        let listener = tokio::net::TcpListener::bind(&addr)
            .await
            .map_err(|e| format!("Failed to bind to {}: {}", addr, e))?;

        axum::serve(listener, app)
            .await
            .map_err(|e| format!("Server error: {}", e))?;

        Ok(())
    }
}
