use anyhow::Result;
use aws_sdk_s3::Client;
use aws_sdk_s3::config::{Credentials, Region};
use clap::Parser;
use config::{Config, Environment, File};
use log::{error, info};
use pcap::{Capture, Device, Linktype, Packet};
use serde::Deserialize;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

// Re-export for easier access
use pcap::Savefile as PcapSavefile;
use std::fs::File as StdFile;

#[derive(Debug, Deserialize, Clone)]
struct MinioConfig {
    endpoint: String,
    access_key: String,
    secret_key: String,
    bucket: String,
    use_ssl: bool,
}

#[derive(Debug, Deserialize, Clone)]
struct AppConfig {
    interface: String,
    pcap_dir: String,
    capture_duration_seconds: u64,
    max_file_size_mb: u64,
    minio: MinioConfig,
}

impl AppConfig {
    fn load() -> Result<Self, config::ConfigError> {
        let config_dir = std::env::current_dir().unwrap_or_else(|_| std::path::PathBuf::from("."));
        let config = Config::builder()
            .add_source(File::with_name("config").required(false))
            .add_source(File::from(config_dir.join("config.toml")).required(false))
            .add_source(Environment::with_prefix("TRAFFIC_CAPTURE")
                .separator("__")
                .list_separator(","))
            .build()?;

        config.try_deserialize()
    }
}

fn ensure_pcap_dir(path: &str) -> Result<(), std::io::Error> {
    std::fs::create_dir_all(path)
}

#[derive(Parser, Debug)]
#[command(version, about, long_about = None)]
struct Args {
    /// Path to the configuration file
    #[arg(short, long)]
    config_file: Option<PathBuf>,
}

fn setup_logging() -> Result<()> {
    if std::env::var("RUST_LOG").is_err() {
        std::env::set_var("RUST_LOG", "info");
    }
    pretty_env_logger::init();
    Ok(())
}

fn load_config(config_path: &str) -> Result<AppConfig> {
    let settings = Config::builder()
        .add_source(File::with_name(config_path).required(false))
        .add_source(Environment::with_prefix("TRAFFIC_CAPTURE"))
        .build()?;

    settings.try_deserialize().map_err(Into::into)
}

fn ensure_pcap_dir_exists(dir: &str) -> Result<()> {
    if !std::path::Path::new(dir).exists() {
        fs::create_dir_all(dir)?;
        info!("Created directory: {}", dir);
    }
    Ok(())
}

fn create_pcap_file(dir: &str) -> Result<(PathBuf, pcap::Savefile)> {
    use std::fs::File;
    use std::path::Path;
    
    let timestamp = chrono::Local::now().format("%Y%m%d_%H%M%S").to_string();
    let filename = format!("capture_{}.pcap", timestamp);
    let path = Path::new(dir).join(&filename);
    
    // Create parent directories if they don't exist
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    
    let file = File::create(&path)?;
    let cap = Capture::dead(Linktype::ETHERNET)?;
    let savefile = cap.savefile(&path)?;
    
    info!("Created new capture file: {:?}", path);
    Ok((path, savefile))
}

async fn upload_to_minio(file_path: &Path, config: &MinioConfig) -> Result<()> {
    use aws_sdk_s3::primitives::ByteStream;
    use http::Uri;
    
    let file_name = file_path
        .file_name()
        .and_then(|n| n.to_str())
        .ok_or_else(|| anyhow::anyhow!("Invalid file name"))?
        .to_string();

    // Create the endpoint URI
    let endpoint = if config.use_ssl {
        format!("https://{}", config.endpoint)
    } else {
        format!("http://{}", config.endpoint)
    };
    
    // Create credentials
    let credentials = Credentials::new(
        &config.access_key,
        &config.secret_key,
        None, // session token
        None, // expires_after
        "minio", // provider name
    );
    
    // Load configuration from environment
    let sdk_config = aws_config::load_from_env().await;
    
    // Create the S3 client with custom endpoint
    let s3_config = aws_sdk_s3::config::Builder::from(&sdk_config)
        .region(Region::new("us-east-1"))
        .credentials_provider(credentials)
        .endpoint_url(&endpoint)
        .force_path_style(true)
        .build();
    
    let client = Client::from_conf(s3_config);
    
    // Read the file into a byte stream using the correct ByteStream type
    let body = ByteStream::from_path(file_path)
        .await
        .map_err(|e| anyhow::anyhow!("Failed to read file: {}", e))?;
    
    // Upload the file to MinIO
    client
        .put_object()
        .bucket(&config.bucket)
        .key(&file_name)  // Borrow file_name instead of moving it
        .body(body)
        .send()
        .await
        .map_err(|e| anyhow::anyhow!("Failed to upload to MinIO: {}", e))?;
        
    info!("Successfully uploaded {} to MinIO", file_name);
    Ok(())
}

async fn capture_traffic(config: &AppConfig) -> Result<()> {
    use std::time::SystemTime;
    
    // Get the default device if no interface is specified
    let device = if config.interface.is_empty() {
        // Get all devices and find the first non-loopback one
        let devices = Device::list()?;
        devices
            .into_iter()
            .find(|d| !d.name.to_lowercase().contains("lo"))  // Simple check for non-loopback
            .ok_or_else(|| anyhow::anyhow!("No suitable network device found"))?
            .name
    } else {
        config.interface.clone()
    };
    
    let mut cap = Capture::from_device(device.as_str())?
        .promisc(true)
        .snaplen(65535)
        .timeout(1000)
        .open()?;
    
    let (mut current_file, mut savefile) = create_pcap_file(&config.pcap_dir)?;
    let mut packet_count = 0;
    let start_time = Instant::now();
    let max_packets = (config.max_file_size_mb * 1_000_000) / 1500; // Rough estimate
    
    info!("Starting capture on interface {}...", config.interface);
    
    loop {
        match cap.next() {
            Ok(packet) => {
                // Write the packet to the current file
                // Create a new Packet with the correct lifetime
                let pkt = Packet::new(packet.header, &packet.data[..packet.header.caplen as usize]);
                savefile.write(&pkt);
                
                packet_count += 1;
                
                // Rotate file if we've reached the max size or time
                if packet_count >= max_packets as usize || 
                   start_time.elapsed().as_secs() >= config.capture_duration_seconds {
                    // Close the current file
                    drop(savefile);
                    
                    // Upload the file to MinIO
                    if let Err(e) = upload_to_minio(&current_file, &config.minio).await {
                        error!("Failed to upload {} to MinIO: {}", current_file.display(), e);
                    } else {
                        info!("Successfully uploaded {} to MinIO", current_file.display());
                        // Optionally delete the file after successful upload
                        if let Err(e) = std::fs::remove_file(&current_file) {
                            error!("Failed to delete {}: {}", current_file.display(), e);
                        }
                    }
                    
                    // Create a new file
                    let (new_file, new_savefile) = create_pcap_file(&config.pcap_dir)?;
                    current_file = new_file;
                    savefile = new_savefile;
                    packet_count = 0;
                    
                    info!("Rotated to new capture file: {:?}", current_file);
                }
            }
            Err(e) => {
                error!("Error capturing packet: {}", e);
                // Add a small delay to prevent tight loop on errors
                tokio::time::sleep(Duration::from_millis(100)).await;
            }
        }
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    // Setup logging
    setup_logging()?;

    let args = Args::parse();
    
    // Load configuration
    let config = if let Some(config_path) = args.config_file {
        // Load from specified config file
        let config = Config::builder()
            .add_source(File::with_name(&config_path.to_string_lossy()).required(true))
            .add_source(Environment::with_prefix("TRAFFIC_CAPTURE")
                .separator("__")
                .list_separator(","))
            .build()?;
        config.try_deserialize()?
    } else {
        // Try to load from default locations
        AppConfig::load()?
    };
    
    info!("Starting traffic capture with config: {:#?}", config);
    
    // Create pcap directory if it doesn't exist
    ensure_pcap_dir(&config.pcap_dir)?;
    
    // Start capturing traffic
    capture_traffic(&config).await
}
