mod config;
mod edge;
mod mesh;
mod relay;

use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .init();

    tracing::info!("entrouter-line starting");

    // TODO: Load config, init tunnels, start relay
    tokio::signal::ctrl_c().await.ok();
    tracing::info!("shutting down");
}
