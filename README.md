# igpsport-downloader

Pulls your activities (fit files) out of iGPSport (Europe/Global) platform and drops them into a watch folder.

# Configuration

It is designed to be run periodically and features automatic deduplication, HTTP retries, and log rotation. It checks the **last 20 activities**, so it should typically run at least frequently enough to cause overlaps.
The script uses environment variables to keep your credentials secure. You need to create a .env file

## docker-compose.yml
```
services:
  igpsport-downloader:
    image: ghcr.io/effectpears/igpsport-downloader:latest
    container_name: igpsport-downloader
    env_file:
      - .env
    environment:
      TZ: Europe/Berlin
      IGPSPORT_DOWNLOAD_DIR: /app/fit_files
      IGPSPORT_LOG_DIR: /app/logs
    volumes:
      - ./watch:/app/fit_files      # => Folder for the fit files & download check
      - ./logs:/app/logs            # => Folder for the log files
    restart: unless-stopped
```
## .env file
```
IGPSPORT_USERNAME='your_email'
IGPSPORT_PASSWORD='your_password'
RUN_INTERVAL_SECONDS=3600        # => every 1h
```

# Information

As a transparency note, the tool is vibe coded with GitHub Copilot.

## Not affiliated with igpsport
