//! Umi CLI
//!
//! Command-line interface for the Umi memory system.
//!
//! # Usage
//!
//! ```bash
//! # Store a value
//! umi store key "value"
//!
//! # Read a value
//! umi read key
//!
//! # Run DST tests
//! umi test --seed 42
//! ```

use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "umi")]
#[command(about = "Umi memory system CLI", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Store a value
    Store {
        /// Key to store
        key: String,
        /// Value to store
        value: String,
    },
    /// Read a value
    Read {
        /// Key to read
        key: String,
    },
    /// Run DST tests
    Test {
        /// Random seed for reproducibility
        #[arg(long)]
        seed: Option<u64>,
    },
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Store { key, value } => {
            println!("Storing {} = {}", key, value);
            // TODO: Implement actual storage
        }
        Commands::Read { key } => {
            println!("Reading {}", key);
            // TODO: Implement actual read
        }
        Commands::Test { seed } => {
            println!("Running DST tests with seed: {:?}", seed);
            // TODO: Implement test runner
        }
    }

    Ok(())
}
