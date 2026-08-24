# igpsport-downloader

A standalone Python script to automatically fetch your latest cycling activities as .fit files from the iGPSport (Europe/Global) platform. It is designed to be run periodically (configurated in the .env) and features automatic deduplication, HTTP retries, and log rotation. It checks the last 20 activities, so it should typically run at least frequently enough to cause overlaps.

# Configuration
The script uses environment variables to keep your credentials secure. You need to create a .env file

# Information

As a transparency note, the tool is vibe coded with GitHub Copilot.
