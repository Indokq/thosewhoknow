#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Mitmproxy script for intercepting and modifying Warp API requests
"""

import json
import sqlite3
import time
import urllib3
import re
import random
import string
from mitmproxy import http
from mitmproxy.script import concurrent
from languages import get_language_manager, _

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def randomize_uuid_string(uuid_str):
    """
    Randomize a UUID string - letters are replaced with hexadecimal letters, numbers with random digits
    Hyphen (-) characters are kept, original casing is preserved

    Args:
        uuid_str (str): UUID formatted string (e.g. 4d22323e-1ce9-44c1-a922-112a718ea3fc)

    Returns:
        str: Randomized UUID string
    """
    hex_digits_lower = '0123456789abcdef'
    hex_digits_upper = '0123456789ABCDEF'

    result = []
    for char in uuid_str:
        if char == '-':
            # Keep the hyphen character
            result.append(char)
        elif char.isdigit():
            # Replace digits with random hexadecimal characters (0-9 or a-f)
            result.append(random.choice(hex_digits_lower))
        elif char in 'abcdef':
            # Replace lowercase hexadecimal letters with random lowercase hexadecimal letters
            result.append(random.choice(hex_digits_lower))
        elif char in 'ABCDEF':
            # Replace uppercase hexadecimal letters with random uppercase hexadecimal letters
            result.append(random.choice(hex_digits_upper))
        else:
            # Leave other characters untouched (for safety)
            result.append(char)

    return ''.join(result)


def generate_experiment_id():
    """Generate a UUID in Warp Experiment ID format"""
    # Format: 931df166-756c-4d4c-b486-4231224bc531
    # Structure: 8-4-4-4-12 hex characters
    def hex_chunk(length):
        return ''.join(random.choice('0123456789abcdef') for _ in range(length))

    return f"{hex_chunk(8)}-{hex_chunk(4)}-{hex_chunk(4)}-{hex_chunk(4)}-{hex_chunk(12)}"

class WarpProxyHandler:
    def __init__(self):
        self.db_path = "accounts.db"
        self.active_token = None
        self.active_email = None
        self.token_expiry = None
        self.last_trigger_check = 0
        self.last_token_check = 0
        self.user_settings_cache = None

    def get_active_account(self):
        """Retrieve the active account from the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # First fetch the active account
            cursor.execute('SELECT value FROM proxy_settings WHERE key = ?', ('active_account',))
            active_result = cursor.fetchone()

            if active_result:
                active_email = active_result[0]
                # Then get account data
                cursor.execute('SELECT account_data FROM accounts WHERE email = ?', (active_email,))
                account_result = cursor.fetchone()

                if account_result:
                    account_data = json.loads(account_result[0])
                    conn.close()
                    return active_email, account_data

            conn.close()
            return None, None
        except Exception as e:
            print(f"Active account lookup error: {e}")
            return None, None

    def update_active_token(self):
        """Update token information for the active account"""
        try:
            print("🔍 Checking active account...")
            email, account_data = self.get_active_account()
            if not account_data:
                print("❌ Active account not found")
                self.active_token = None
                self.active_email = None
                return False

            old_email = self.active_email

            current_time = int(time.time() * 1000)
            token_expiry = account_data['stsTokenManager']['expirationTime']

            # Refresh the token if less than 1 minute remains
            if current_time >= (token_expiry - 60000):  # 1 dakika = 60000ms
                print(f"Refreshing token: {email}")
                if self.refresh_token(email, account_data):
                    # Fetch updated data
                    email, account_data = self.get_active_account()
                    if account_data:
                        self.active_token = account_data['stsTokenManager']['accessToken']
                        self.token_expiry = account_data['stsTokenManager']['expirationTime']
                        self.active_email = email
                        print(f"Token refreshed: {email}")
                        return True
                return False
            else:
                self.active_token = account_data['stsTokenManager']['accessToken']
                self.token_expiry = token_expiry
                self.active_email = email

                if old_email != email:
                    print(f"🔄 Active account switched: {old_email} → {email}")
                else:
                    print(f"✅ Token active: {email}")
                return True
        except Exception as e:
            print(f"Token update error: {e}")
            return False

    def check_account_change_trigger(self):
        """Check trigger file signalling active account change"""
        try:
            trigger_file = "account_change_trigger.tmp"
            import os

            if os.path.exists(trigger_file):
                # Check file modification time
                mtime = os.path.getmtime(trigger_file)
                print(f"📁 Trigger file detected - mtime: {mtime}, last_check: {self.last_trigger_check}")
                if mtime > self.last_trigger_check:
                    print("🔄 Account change trigger detected!")
                    self.last_trigger_check = mtime

                    # Remove trigger file
                    try:
                        os.remove(trigger_file)
                        print("🗑️  Trigger file deleted")
                    except Exception as e:
                        print(f"Trigger file deletion error: {e}")

                    # Update token
                    print("🔄 Refreshing token information...")
                    self.update_active_token()
                    return True
                else:
                    print("⏸️  Trigger file already processed, skipping")
            return False
        except Exception as e:
            print(f"Trigger check error: {e}")
            return False

    def refresh_token(self, email, account_data):
        """Refresh Firebase token"""
        try:
            import requests

            refresh_token = account_data['stsTokenManager']['refreshToken']
            api_key = account_data['apiKey']

            url = f"https://securetoken.googleapis.com/v1/token?key={api_key}"
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token
            }

            # Connect without proxy
            proxies = {'http': None, 'https': None}
            response = requests.post(url, json=data, timeout=30, verify=False, proxies=proxies)

            if response.status_code == 200:
                token_data = response.json()
                new_token_data = {
                    'accessToken': token_data['access_token'],
                    'refreshToken': token_data['refresh_token'],
                    'expirationTime': int(time.time() * 1000) + (int(token_data['expires_in']) * 1000)
                }

                # Update database
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT account_data FROM accounts WHERE email = ?', (email,))
                result = cursor.fetchone()

                if result:
                    account_data = json.loads(result[0])
                    account_data['stsTokenManager'].update(new_token_data)

                    cursor.execute('''
                        UPDATE accounts SET account_data = ?, last_updated = CURRENT_TIMESTAMP
                        WHERE email = ?
                    ''', (json.dumps(account_data), email))
                    conn.commit()

                conn.close()
                return True
            return False
        except Exception as e:
            print(f"Token refresh error: {e}")
            return False

    def mark_account_as_banned(self, email):
        """Mark an account as banned"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Update account health_status to 'banned'
            cursor.execute('''
                UPDATE accounts SET health_status = 'banned', last_updated = CURRENT_TIMESTAMP
                WHERE email = ?
            ''', (email,))
            conn.commit()
            conn.close()

            print(f"Account marked as banned: {email}")

            # Clear active account (a banned account cannot remain active)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM proxy_settings WHERE key = ?', ('active_account',))
            conn.commit()
            conn.close()

            # Clear active account data in handler
            self.active_token = None
            self.active_email = None
            self.token_expiry = None

            print("Banned account removed from active list")

            # Notify GUI about ban
            self.notify_gui_about_ban(email)
            return True

        except Exception as e:
            print(f"Account ban mark error: {e}")
            return False

    def notify_gui_about_ban(self, email):
        """Send a ban notification to the GUI using a temp file"""
        try:
            import os
            import time

            # Create ban notification file
            ban_notification_file = "ban_notification.tmp"
            with open(ban_notification_file, 'w', encoding='utf-8') as f:
                f.write(f"{email}|{int(time.time())}")

            print(f"Ban notification file created: {ban_notification_file}")
        except Exception as e:
            print(f"Ban notification error: {e}")

    def load_user_settings(self):
        """Load user_settings.json"""
        try:
            import os
            if os.path.exists("user_settings.json"):
                with open("user_settings.json", 'r', encoding='utf-8') as f:
                    self.user_settings_cache = json.load(f)
                print("✅ user_settings.json loaded successfully")
                return True
            else:
                print("⚠️ user_settings.json not found")
                self.user_settings_cache = None
                return False
        except Exception as e:
            print(f"user_settings.json load error: {e}")
            self.user_settings_cache = None
            return False

    def refresh_user_settings(self):
        """Reload user_settings.json"""
        print("🔄 Reloading user_settings.json...")
        return self.load_user_settings()

# Global handler instance
handler = WarpProxyHandler()

def is_relevant_request(flow: http.HTTPFlow) -> bool:
    """Determine whether the request should be handled"""

    # Exclude Firebase token refresh requests initiated by WarpAccountManager itself
    if ("securetoken.googleapis.com" in flow.request.pretty_host and
        flow.request.headers.get("User-Agent") == "WarpAccountManager/1.0"):
        return False

    # Ignore requests originating from WarpAccountManager
    if flow.request.headers.get("X-Warp-Manager-Request") == "true":
        return False

    # Only process specific domains
    relevant_domains = [
        "app.warp.dev",
        "dataplane.rudderstack.com"  # Blocked on purpose
    ]

    # Let unrelated traffic pass silently
    if not any(domain in flow.request.pretty_host for domain in relevant_domains):
        return False

    return True

@concurrent
def request(flow: http.HTTPFlow) -> None:
    """Handle outbound requests"""

    # Filter out irrelevant requests immediately
    if not is_relevant_request(flow):
        # Forward all non-Warp traffic untouched
        return

    request_url = flow.request.pretty_url

    # Block *.dataplane.rudderstack.com requests
    if "dataplane.rudderstack.com" in flow.request.pretty_host:
        print(f"🚫 Rudderstack request blocked: {request_url}")
        flow.response = http.Response.make(
            204,  # No Content
            b"",
            {"Content-Type": "text/plain"}
        )
        return

    print(f"🌐 Warp request: {flow.request.method} {flow.request.pretty_url}")

    # Detect CreateGenericStringObject requests to trigger user_settings.json refresh
    if ("/graphql/v2?op=CreateGenericStringObject" in request_url and
        flow.request.method == "POST"):
        print("🔄 CreateGenericStringObject request detected - refreshing user_settings.json...")
        handler.refresh_user_settings()

    # Check account change triggers for every request
    if handler.check_account_change_trigger():
        print("🔄 Trigger detected and token refreshed!")

    # Display currently active account
    print(f"📧 Active account: {handler.active_email}")

    # Trigger token check every minute
    current_time = time.time()
    if current_time - handler.last_token_check > 60:  # 60 seconds
        print("⏰ Token check due, refreshing...")
        handler.update_active_token()
        handler.last_token_check = current_time

    # Ensure an active account exists
    if not handler.active_email:
        print("❓ Active account missing, checking token...")
        handler.update_active_token()

    # Update Authorization header
    if handler.active_token:
        old_auth = flow.request.headers.get("Authorization", "Yok")
        new_auth = f"Bearer {handler.active_token}"
        flow.request.headers["Authorization"] = new_auth

        print(f"🔑 Authorization header updated for: {handler.active_email}")

        # Ensure the token actually changed
        if old_auth == new_auth:
            print("   ⚠️  WARNING: Old and new tokens are identical!")
        else:
            print("   ✅ Token replaced successfully")

        # Show token suffix for verification
        if len(handler.active_token) > 100:
            print(f"   Token suffix: ...{handler.active_token[-20:]}")

    else:
        print("❌ NO ACTIVE TOKEN - HEADER NOT UPDATED!")
        print(f"   Active email: {handler.active_email}")
        print(f"   Token present: {handler.active_token is not None}")

    # Randomize the X-Warp-Experiment-Id header for app.warp.dev requests
    existing_experiment_id = flow.request.headers.get("X-Warp-Experiment-Id")
    if existing_experiment_id and "app.warp.dev" in flow.request.pretty_host:
        randomized_experiment_id = randomize_uuid_string(existing_experiment_id)
        flow.request.headers["X-Warp-Experiment-Id"] = randomized_experiment_id

        print(f"🧪 Experiment ID randomized ({flow.request.path}):")
        print(f"   Previous: {existing_experiment_id}")
        print(f"   Updated:  {randomized_experiment_id}")

def responseheaders(flow: http.HTTPFlow) -> None:
    """Handle response headers to manage streaming"""
    if not is_relevant_request(flow):
        return

    if "/ai/multi-agent" in flow.request.path:
        flow.response.stream = True
        print(f"[{time.strftime('%H:%M:%S')}] Streaming enabled: {flow.request.pretty_url}")
    else:
        flow.response.stream = False

@concurrent
def response(flow: http.HTTPFlow) -> None:
    """Handle inbound responses"""

    # Ignore Firebase token refresh requests initiated by WarpAccountManager
    if ("securetoken.googleapis.com" in flow.request.pretty_host and
        flow.request.headers.get("User-Agent") == "WarpAccountManager/1.0"):
        return

    # Process only app.warp.dev domain
    if "app.warp.dev" not in flow.request.pretty_host:
        return

    # Filter irrelevant requests quietly
    if not is_relevant_request(flow):
        return

    # Exclude requests originating from WarpAccountManager
    if flow.request.headers.get("X-Warp-Manager-Request") == "true":
        return

    print(f"📡 Warp response: {flow.response.status_code} - {flow.request.pretty_url}")

    # Use cached response for GetUpdatedCloudObjects
    if ("/graphql/v2?op=GetUpdatedCloudObjects" in flow.request.pretty_url and
        flow.request.method == "POST" and
        flow.response.status_code == 200 and
        handler.user_settings_cache is not None):
        print("🔄 Replacing GetUpdatedCloudObjects response with cached data...")
        try:
            # Convert cached data to JSON string
            cached_response = json.dumps(handler.user_settings_cache, ensure_ascii=False)

            # Replace response body
            flow.response.content = cached_response.encode('utf-8')
            flow.response.headers["Content-Length"] = str(len(flow.response.content))
            flow.response.headers["Content-Type"] = "application/json"

            print("✅ GetUpdatedCloudObjects response replaced successfully")
        except Exception as e:
            print(f"❌ Response replacement error: {e}")

    # Treat 403 responses on /ai/multi-agent as account bans
    if "/ai/multi-agent" in flow.request.path and flow.response.status_code == 403:
        print("⛔ 403 FORBIDDEN - Account appears to be banned!")
        if handler.active_email:
            print(f"Banned account: {handler.active_email}")
            handler.mark_account_as_banned(handler.active_email)
        else:
            print("Active account missing, unable to mark as banned")

    # Attempt token refresh on HTTP 401
    if flow.response.status_code == 401:
        print("401 received, refreshing token...")
        if handler.update_active_token():
            print("Token refreshed, retry the request")

# Load active account on start
def load(loader):
    """Executed when the script starts"""
    print("Warp Proxy Script started")
    print("Checking database connection...")
    handler.update_active_token()
    if handler.active_email:
        print(f"Active account loaded: {handler.active_email}")
        print(f"Token available: {handler.active_token is not None}")
    else:
        print("No active account found - remember to activate one!")

    # Load user_settings.json
    print("Loading user_settings.json...")
    handler.load_user_settings()

def done():
    """Executed when the script stops"""
    print("Warp Proxy Script stopped")
