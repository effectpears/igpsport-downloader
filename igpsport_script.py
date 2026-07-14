#!/usr/bin/env python3
"""
AI-Information: vibe coded with github copilot

Download FIT files from iGPSport (Global/Europe) - Standalone Operation
Captures late uploads by tracking the sync state.

- Checks the last 20 activities
- Uses .env file for configuration
"""

import requests
import json
from datetime import datetime
import os
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ===== LOAD CONFIGURATION =====
# Loads environment variables from the .env file
load_dotenv()

USERNAME = os.getenv("IGPSPORT_USERNAME")
PASSWORD = os.getenv("IGPSPORT_PASSWORD")
DOWNLOAD_DIR = os.getenv("IGPSPORT_DOWNLOAD_DIR", "./fit_files")
LOG_DIR = os.getenv("IGPSPORT_LOG_DIR", "./logs")

# Keep the state file in the download directory so it persists with the data
SYNC_STATE_FILE = os.path.join(DOWNLOAD_DIR, ".igpsport_sync_state.json")

if not USERNAME or not PASSWORD:
    raise ValueError("Missing IGPSPORT_USERNAME or IGPSPORT_PASSWORD in your .env file.")

# ===== LOGGING SETUP =====
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Standard File Handler with rotation
log_file_path = os.path.join(LOG_DIR, "igpsport_download.log")
fh = RotatingFileHandler(
    log_file_path,
    maxBytes=1024*1024,  # 1MB
    backupCount=1
)
fh.setLevel(logging.INFO)

# Console Handler
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
fh.setFormatter(formatter)
ch.setFormatter(formatter)

logger.addHandler(fh)
logger.addHandler(ch)

# ===== EUROPE (GLOBAL) CONFIGURATION =====
BASE_URL = "https://prod.en.igpsport.com/service"
ORIGIN = "https://login.passport.igpsport.com"
REFERER = "https://login.passport.igpsport.com/"

class IGPSportClient:
    """Client for the iGPSport API"""
    
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.token = None
        self.session = requests.Session()
        
        # Setup retry strategy for robust network operations
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # IMPORTANT: The correct headers are essential for the Europe region!
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": ORIGIN,
            "Referer": REFERER,
        })
    
    def login(self) -> bool:
        """Authenticate with iGPSport"""
        logger.info("Logging into iGPSport...")
        
        url = f"{BASE_URL}/auth/account/login"
        # IMPORTANT: Send password in PLAINTEXT (not MD5!)
        payload = {
            "username": self.username,
            "password": self.password,
            "appId": "igpsport-web",
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=15)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("code") != 0:
                logger.error(f"Login failed: {result.get('message')}")
                return False
            
            access_token = result.get("data", {}).get("access_token")
            if not access_token:
                logger.error("No access token received")
                return False
            
            self.token = access_token
            self.session.headers.update({"Authorization": f"Bearer {access_token}"})
            logger.info("✓ Login successful!")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Login error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return False
    
    def get_recent_activities(self) -> list:
        """Fetch the last 20 activities"""
        logger.info("Fetching the last 20 activities...")
        
        if not self.token:
            logger.error("Not logged in!")
            return []
        
        url = f"{BASE_URL}/web-gateway/web-analyze/activity/queryMyActivity"
        
        params = {
            "pageNo": 1,
            "pageSize": 20,  # Strict limit to the last 20 activities
            "reqType": 0,
            "sort": 1
        }
        
        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("code") != 0:
                logger.error(f"Error fetching activities: {result.get('message')}")
                return []
            
            activities = result.get("data", {}).get("rows", [])
            logger.info(f"✓ Found {len(activities)} activities in the current page")
            
            filtered = []
            for activity in activities:
                try:
                    activity_id = activity.get("rideId")
                    detail = self.get_activity_detail(activity_id)
                    
                    if detail:
                        start_time_str = detail.get("startTime", "")
                        if start_time_str:
                            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                            fit_url = detail.get("fitUrl") or activity.get("fitOssPath")
                            
                            if fit_url:
                                filtered.append({
                                    "id": activity_id,
                                    "name": activity.get("name", f"Activity_{activity_id}"),
                                    "start_time": start_time,
                                    "fit_url": fit_url,
                                })
                except Exception as e:
                    logger.warning(f"Error processing activity ID {activity.get('rideId')}: {e}")
                    continue
            
            return filtered
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching activities: {e}")
            return []
    
    def get_activity_detail(self, activity_id: int) -> dict:
        """Fetch details for a specific activity"""
        if not self.token:
            return {}
        
        url = f"{BASE_URL}/web-gateway/web-analyze/activity/queryActivityDetail/{activity_id}"
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("code") == 0:
                return result.get("data", {})
            
            return {}
            
        except Exception as e:
            logger.warning(f"Error fetching activity details for ID {activity_id}: {e}")
            return {}
    
    def download_fit_file(self, fit_url: str, filename: str) -> bool:
        """Download the FIT file"""
        if not fit_url:
            logger.warning(f"No FIT URL provided for {filename}")
            return False
        
        try:
            response = self.session.get(fit_url, stream=True, timeout=30)
            response.raise_for_status()
            
            filepath = os.path.join(DOWNLOAD_DIR, filename)
            downloaded_size = 0
            
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
            
            if downloaded_size > 0:
                logger.info(f"  ✓ {filename} ({downloaded_size} bytes)")
                return True
            else:
                logger.warning(f"  ✗ Empty file: {filename}")
                # Clean up empty file
                os.remove(filepath)
                return False
                
        except Exception as e:
            logger.error(f"  ✗ Download failed: {e}")
            return False


def load_sync_state() -> dict:
    """Load the sync state"""
    try:
        if os.path.exists(SYNC_STATE_FILE):
            with open(SYNC_STATE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Error loading sync state: {e}")
    
    return {"downloaded_ids": []}


def get_downloaded_ids() -> set:
    """Get the set of already downloaded activity IDs"""
    state = load_sync_state()
    return set(state.get("downloaded_ids", []))


def save_sync_state(downloaded_ids: set):
    """Save the sync state"""
    try:
        state = {
            "downloaded_ids": list(downloaded_ids),
            "timestamp": datetime.now().isoformat()
        }
        
        with open(SYNC_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
            
        logger.info(f"✓ Sync state saved (Total downloaded IDs: {len(downloaded_ids)})")
    except Exception as e:
        logger.error(f"Error saving sync state: {e}")


def file_exists(activity_id: int, start_time: datetime) -> bool:
    """Check if the FIT file already exists in the download directory"""
    timestamp = start_time.strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_{activity_id}.fit"
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    return os.path.exists(filepath)


def main():
    logger.info("=" * 70)
    logger.info("iGPSport FIT Downloader Started")
    logger.info("=" * 70)
    
    # Create download directory
    Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
    logger.info(f"Storage path: {os.path.abspath(DOWNLOAD_DIR)}\n")
    
    downloaded_ids = get_downloaded_ids()
    
    # Initialize client and login
    client = IGPSportClient(USERNAME, PASSWORD)
    
    if not client.login():
        logger.error("Authentication failed!")
        logger.info("=" * 70)
        return
    
    logger.info("")
    
    # Fetch the last 20 activities
    activities = client.get_recent_activities()
    
    if not activities:
        logger.info("No activities found")
        logger.info("=" * 70)
        return
    
    logger.info(f"\nProcessing {len(activities)} activities...\n")
    
    # Process files
    success_count = 0
    skipped_count = 0
    error_count = 0
    
    for activity in activities:
        activity_id = activity["id"]
        start_time = activity["start_time"]
        fit_url = activity["fit_url"]
        
        timestamp = start_time.strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{activity_id}.fit"
        
        activity_name = activity["name"]
        logger.info(f"Activity: {activity_name}")
        logger.info(f"  Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')} | ID: {activity_id}")
        
        # Check if already downloaded (deduplication)
        if file_exists(activity_id, start_time) or activity_id in downloaded_ids:
            logger.info(f"  Status: ⊘ Already exists (skipped)\n")
            skipped_count += 1
            downloaded_ids.add(activity_id)
        else:
            if client.download_fit_file(fit_url, filename):
                logger.info(f"  Status: ✓ Successfully downloaded\n")
                success_count += 1
                downloaded_ids.add(activity_id)
            else:
                logger.error(f"  Status: ✗ Download failed\n")
                error_count += 1
    
    # Summary
    logger.info("=" * 70)
    logger.info("SUMMARY:")
    logger.info(f"  ✓ New files: {success_count}")
    logger.info(f"  ⊘ Already existed: {skipped_count}")
    logger.info(f"  ✗ Errors: {error_count}")
    logger.info(f"  TOTAL: {len(activities)} activities processed")
    logger.info("=" * 70)
    
    # Save the sync state
    save_sync_state(downloaded_ids)
    
    logger.info("Downloader finished")


if __name__ == "__main__":
    main()
