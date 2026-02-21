//! PAPA Lang (PL) — AI-native programming language.
//!
//! CLI: pl run, pl build, pl deploy, pl migrate, pl test, pl fmt, pl lint, pl repl

use clap::{Parser, Subcommand};
use papa_lang::lexer::Scanner;
use papa_lang::parser::Parser as PlParser;
use std::fs;
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "pl")]
#[command(about = "PAPA Lang — AI-native programming language", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Run a PL file (interpret)
    Run {
        #[arg(value_name = "FILE")]
        file: PathBuf,
        /// Port for HTTP server (future)
        #[arg(long)]
        port: Option<u16>,
    },
    /// Run a PL file that starts an HTTP server (server + routes + app.start)
    Serve {
        #[arg(value_name = "FILE")]
        file: PathBuf,
        #[arg(long)]
        port: Option<u16>,
    },
    /// List runtime engines and their status
    Engines,
    /// Compile to binary (future)
    Build {
        #[arg(value_name = "FILE")]
        file: PathBuf,
    },
    /// Deploy to environment (future)
    Deploy {
        #[arg(value_name = "ENV", default_value = "dev")]
        env: String,
    },
    /// Run database migrations (future)
    Migrate {
        #[arg(long)]
        rollback: bool,
    },
    /// Run tests (future)
    Test,
    /// Format code (future)
    Fmt {
        #[arg(value_name = "FILE")]
        files: Vec<PathBuf>,
    },
    /// Lint code (future)
    Lint,
    /// Interactive REPL (future)
    Repl,
}

fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Engines => {
            println!("PAPA Lang Runtime Engines:");
            println!("  ✅ db        — Built-in database (SQLite)");
            println!("  ✅ cache     — In-memory cache with TTL");
            println!("  ✅ http      — HTTP server (axum)");
            println!("  ✅ ai        — Multi-provider AI routing");
            println!("  ✅ log       — Structured logging");
            println!("  ✅ metrics   — Counters & gauges");
            println!("  ✅ secrets   — Environment-based secrets");
            println!("  ✅ storage   — File-based object storage");
            println!("  ✅ queue     — In-memory job queues");
            println!("  ✅ crypto    — JWT, bcrypt, UUID");
        }
        Commands::Run { file, port }
        | Commands::Serve { file, port } => {
            if let Some(p) = port {
                std::env::set_var("PAPA_PORT", p.to_string());
            }
            let source = fs::read_to_string(&file)
                .map_err(|e| anyhow::anyhow!("Failed to read {}: {}", file.display(), e))?;
            let mut scanner = Scanner::new(&source);
            let tokens = scanner.scan_all();
            let mut parser = PlParser::new(tokens);
            let program = parser.parse();

            let mut evaluator = papa_lang::interpreter::Evaluator::new();
            evaluator
                .eval_program(&program)
                .map_err(|e| anyhow::anyhow!("Runtime error: {}", e))?;
        }
        Commands::Build { file: _ } => {
            println!("Build not implemented yet");
        }
        Commands::Deploy { env } => {
            println!("Deploy to {} not implemented yet", env);
        }
        Commands::Migrate { rollback } => {
            println!("Migrate {} not implemented yet", if rollback { "rollback" } else { "" });
        }
        Commands::Test => {
            println!("Test not implemented yet");
        }
        Commands::Fmt { files: _ } => {
            println!("Fmt not implemented yet");
        }
        Commands::Lint => {
            println!("Lint not implemented yet");
        }
        Commands::Repl => {
            println!("REPL not implemented yet");
        }
    }

    Ok(())
}
