#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import sqlite3
import requests
import time
import subprocess
import os
import psutil
import urllib3
from pathlib import Path
from languages import get_language_manager, _
from warp_bridge_server import WarpBridgeServer
IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = not IS_WINDOWS and not IS_MACOS

# Platform-specific imports
if IS_WINDOWS:
    import winreg
    from windows_bridge_config import BridgeConfig
elif IS_MACOS:
    # macOS - no winreg needed
    winreg = None
    from macos_bridge_config import MacOSBridgeConfig as BridgeConfig
else:
    # Linux or other platforms
    winreg = None
    BridgeConfig = None

# Suppress SSL warnings when using mitmproxy
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QPushButton, QTableWidget, QTableWidgetItem,
                             QDialog, QTextEdit, QLabel, QMessageBox, QHeaderView,
                             QProgressDialog, QAbstractItemView, QStatusBar, QMenu, QAction, QScrollArea, QComboBox, QTabWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QObject
from PyQt5.QtGui import QFont


def get_os_info():
    """Get operating system information for API headers"""
    import platform

    if IS_WINDOWS:
        return {
            'category': 'Windows',
            'name': 'Windows',
            'version': f'{platform.release()} ({platform.version()})'
        }
    elif IS_MACOS:
        return {
            'category': 'Darwin',
            'name': 'macOS',
            'version': platform.mac_ver()[0]
        }
    else:
        # Linux or other
        return {
            'category': 'Linux',
            'name': platform.system(),
            'version': platform.release()
        }


def load_stylesheet(app):
    """Apply the modern compact QSS stylesheet if it exists."""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        style_path = os.path.join(base_dir, "style.qss")
        if os.path.exists(style_path):
            with open(style_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
    except Exception as e:
        print(f"{_('stylesheet_load_error', e)}")


class AccountManager:
    def __init__(self):
        self.db_path = "accounts.db"
        self.init_database()

    def init_database(self):
        """Initialize the database and create required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                account_data TEXT NOT NULL,
                health_status TEXT DEFAULT 'healthy',
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Add health_status column if it does not exist
        try:
            cursor.execute('ALTER TABLE accounts ADD COLUMN health_status TEXT DEFAULT "healthy"')
        except sqlite3.OperationalError:
            # Column already exists
            pass

        # Add limit_info column if it doesn't exist
        try:
            cursor.execute('ALTER TABLE accounts ADD COLUMN limit_info TEXT DEFAULT "Not Updated"')
        except sqlite3.OperationalError:
            # Column already exists
            pass
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS proxy_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')

        # Insert default value for certificate approval status
        cursor.execute('''
            INSERT OR IGNORE INTO proxy_settings (key, value)
            VALUES ('certificate_approved', 'false')
        ''')
        conn.commit()
        conn.close()

    def add_account(self, account_json):
        """Add an account from JSON data"""
        try:
            account_data = json.loads(account_json)
            email = account_data.get('email')

            if not email:
                raise ValueError(_('email_not_found'))

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO accounts (email, account_data, last_updated)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (email, account_json))
            conn.commit()
            conn.close()
            return True, _('account_added_success')
        except json.JSONDecodeError:
            return False, _('invalid_json')
        except Exception as e:
            return False, f"{_('error')}: {str(e)}"

    def get_accounts(self):
        """Return all stored accounts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT email, account_data FROM accounts ORDER BY email')
        accounts = cursor.fetchall()
        conn.close()
        return accounts

    def get_accounts_with_health(self):
        """Return all accounts including their health status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT email, account_data, health_status FROM accounts ORDER BY email')
        accounts = cursor.fetchall()
        conn.close()
        return accounts

    def update_account_health(self, email, health_status):
        """Update the stored health status for an account"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE accounts SET health_status = ?, last_updated = CURRENT_TIMESTAMP
                WHERE email = ?
            ''', (health_status, email))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Health status update error: {e}")
            return False

    def update_account_token(self, email, new_token_data):
        """Update token details for an account"""
        try:
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
            print(f"Token update error: {e}")
            return False

    def update_account(self, email, updated_json):
        """Replace all account data using a JSON string"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE accounts SET account_data = ?, last_updated = CURRENT_TIMESTAMP
                WHERE email = ?
            ''', (updated_json, email))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Account update error: {e}")
            return False

    def set_active_account(self, email):
        """Mark an account as active"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO proxy_settings (key, value)
                VALUES ('active_account', ?)
            ''', (email,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Active account assignment error: {e}")
            return False

    def get_active_account(self):
        """Return the currently active account"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM proxy_settings WHERE key = ?', ('active_account',))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
        except:
            return None

    def clear_active_account(self):
        """Clear the active account flag"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM proxy_settings WHERE key = ?', ('active_account',))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Active account clearing error: {e}")
            return False

    def delete_account(self, email):
        """Delete an account"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Remove the account from the table
            cursor.execute('DELETE FROM accounts WHERE email = ?', (email,))

            # If the deleted account was active, clear the active account entry
            cursor.execute('SELECT value FROM proxy_settings WHERE key = ?', ('active_account',))
            result = cursor.fetchone()
            if result and result[0] == email:
                cursor.execute('DELETE FROM proxy_settings WHERE key = ?', ('active_account',))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Account deletion error: {e}")
            return False

    def update_account_limit_info(self, email, limit_info):
        """Update cached limit information for an account"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE accounts SET limit_info = ?, last_updated = CURRENT_TIMESTAMP
                WHERE email = ?
            ''', (limit_info, email))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Limit information update error: {e}")
            return False

    def get_accounts_with_health_and_limits(self):
        """Return all accounts with health status and limit information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT email, account_data, health_status, limit_info FROM accounts ORDER BY email')
        accounts = cursor.fetchall()
        conn.close()
        return accounts

    def is_certificate_approved(self):
        """Check whether certificate approval was previously recorded"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM proxy_settings WHERE key = ?', ('certificate_approved',))
            result = cursor.fetchone()
            conn.close()
            return result and result[0] == 'true'
        except:
            return False

    def set_certificate_approved(self, approved=True):
        """Persist certificate approval state in the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO proxy_settings (key, value)
                VALUES ('certificate_approved', ?)
            ''', ('true' if approved else 'false',))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Certificate approval save error: {e}")
            return False


class ProxyManager:
    """Cross-platform proxy settings manager"""

    @staticmethod
    def set_proxy(proxy_server):
        """Enable proxy settings"""
        if IS_WINDOWS:
            return ProxyManager._set_proxy_windows(proxy_server)
        elif IS_MACOS:
            return ProxyManager._set_proxy_macos(proxy_server)
        else:
            return True

    @staticmethod
    def _set_proxy_windows(proxy_server):
        """Windows proxy configuration using registry"""
        try:
            if winreg is None:
                return False

            # Registry key opening
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                               0, winreg.KEY_SET_VALUE)

            # Set proxy settings
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, proxy_server)

            winreg.CloseKey(key)

            # Refresh Internet Explorer settings (silently)
            try:
                subprocess.run(["rundll32.exe", "wininet.dll,InternetSetOption", "0", "37", "0", "0"],
                             shell=True, capture_output=True, timeout=5)
            except:
                # If silent refresh doesn't work, inform user
                pass

            return True
        except Exception as e:
            print(f"Proxy setup error: {e}")
            return False

    @staticmethod
    def _set_proxy_macos(proxy_server):
        """macOS proxy configuration using networksetup with PAC file approach"""
        try:
            host, port = proxy_server.split(":")

            # Create PAC file for selective proxy - only Warp domains
            pac_content = f"""function FindProxyForURL(url, host) {{
    // Redirect only Warp-related domains through proxy
    if (shExpMatch(host, "*.warp.dev") ||
        shExpMatch(host, "*warp.dev") ||
        shExpMatch(host, "*.dataplane.rudderstack.com") ||
        shExpMatch(host, "*dataplane.rudderstack.com")) {{
        return "PROXY {host}:{port}";
    }}

    // All other traffic goes direct (preserving internet access)
    return "DIRECT";
}}"""

            # Write PAC file
            import tempfile
            import os
            pac_dir = os.path.expanduser("~/.warp_proxy")
            os.makedirs(pac_dir, exist_ok=True)
            pac_file = os.path.join(pac_dir, "warp_proxy.pac")

            with open(pac_file, 'w') as f:
                f.write(pac_content)

            print(f"PAC file created: {pac_file}")

            # Get active network service
            result = subprocess.run(["networksetup", "-listnetworkserviceorder"],
                                  capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                print("Failed to get network services")
                return False

            # Find the first active service (usually Wi-Fi or Ethernet)
            services = []
            for line in result.stdout.split('\n'):
                if line.startswith('(') and ')' in line:
                    service_name = line.split(') ')[1] if ') ' in line else None
                    if service_name and service_name not in ['Bluetooth PAN', 'Thunderbolt Bridge']:
                        services.append(service_name)

            if not services:
                print("No suitable network service found")
                return False

            primary_service = services[0]
            print(f"Configuring PAC proxy for service: {primary_service}")

            # Set Auto Proxy Configuration (PAC)
            pac_url = f"file://{pac_file}"
            result1 = subprocess.run(["networksetup", "-setautoproxyurl", primary_service, pac_url],
                                   capture_output=True, text=True, timeout=10)

            # Enable auto proxy
            result2 = subprocess.run(["networksetup", "-setautoproxystate", primary_service, "on"],
                                   capture_output=True, text=True, timeout=10)

            if result1.returncode == 0 and result2.returncode == 0:
                print(f"PAC proxy configured successfully: {proxy_server}")
                print("✅ Internet access preserved - only Warp traffic goes through proxy")
                return True
            else:
                print(f"PAC proxy configuration failed. PAC: {result1.stderr}, Enable: {result2.stderr}")
                # Fallback to manual proxy if PAC fails
                print("Falling back to manual proxy configuration...")
                return ProxyManager._set_proxy_macos_manual(proxy_server)

        except Exception as e:
            print(f"macOS PAC proxy setup error: {e}")
            # Fallback to manual proxy
            print("Falling back to manual proxy configuration...")
            return ProxyManager._set_proxy_macos_manual(proxy_server)

    @staticmethod
    def _set_proxy_macos_manual(proxy_server):
        """macOS manual proxy configuration (fallback method)"""
        try:
            host, port = proxy_server.split(":")

            # Get active network service
            result = subprocess.run(["networksetup", "-listnetworkserviceorder"],
                                  capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                print("Failed to get network services")
                return False

            # Find the first active service (usually Wi-Fi or Ethernet)
            services = []
            for line in result.stdout.split('\n'):
                if line.startswith('(') and ')' in line:
                    service_name = line.split(') ')[1] if ') ' in line else None
                    if service_name and service_name not in ['Bluetooth PAN', 'Thunderbolt Bridge']:
                        services.append(service_name)

            if not services:
                print("No suitable network service found")
                return False

            primary_service = services[0]
            print(f"Configuring manual proxy for service: {primary_service}")

            # Set HTTP proxy
            result1 = subprocess.run(["networksetup", "-setwebproxy", primary_service, host, port],
                                   capture_output=True, text=True, timeout=10)

            # Set HTTPS proxy
            result2 = subprocess.run(["networksetup", "-setsecurewebproxy", primary_service, host, port],
                                   capture_output=True, text=True, timeout=10)

            if result1.returncode == 0 and result2.returncode == 0:
                print(f"Manual proxy configured successfully: {proxy_server}")
                print("⚠️ All HTTP/HTTPS traffic will go through proxy")
                return True
            else:
                print(f"Manual proxy configuration failed. HTTP: {result1.stderr}, HTTPS: {result2.stderr}")
                return False

        except Exception as e:
            print(f"macOS manual proxy setup error: {e}")
            return False

    @staticmethod
    def disable_proxy():
        """Disable proxy settings"""
        if IS_WINDOWS:
            return ProxyManager._disable_proxy_windows()
        elif IS_MACOS:
            return ProxyManager._disable_proxy_macos()
        else:
            return True

    @staticmethod
    def _disable_proxy_windows():
        """Disable Windows proxy settings"""
        try:
            if winreg is None:
                return False

            # Open registry key
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                               0, winreg.KEY_SET_VALUE)

            # Disable proxy
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)

            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Proxy disable error: {e}")
            return False

    @staticmethod
    def _disable_proxy_macos():
        """Disable macOS proxy settings (both PAC and manual)"""
        try:
            # Get active network service
            result = subprocess.run(["networksetup", "-listnetworkserviceorder"],
                                  capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                print("Failed to get network services")
                return False

            # Find the first active service
            services = []
            for line in result.stdout.split('\n'):
                if line.startswith('(') and ')' in line:
                    service_name = line.split(') ')[1] if ') ' in line else None
                    if service_name and service_name not in ['Bluetooth PAN', 'Thunderbolt Bridge']:
                        services.append(service_name)

            if not services:
                print("No suitable network service found")
                return False

            primary_service = services[0]
            print(f"Disabling proxy for service: {primary_service}")

            success_count = 0

            # Disable Auto Proxy (PAC)
            result1 = subprocess.run(["networksetup", "-setautoproxystate", primary_service, "off"],
                                   capture_output=True, text=True, timeout=10)
            if result1.returncode == 0:
                success_count += 1
                print("✅ Auto Proxy (PAC) disabled")
            else:
                print(f"⚠️ Auto Proxy disable failed: {result1.stderr}")

            # Disable HTTP proxy
            result2 = subprocess.run(["networksetup", "-setwebproxystate", primary_service, "off"],
                                   capture_output=True, text=True, timeout=10)
            if result2.returncode == 0:
                success_count += 1
                print("✅ HTTP Proxy disabled")
            else:
                print(f"⚠️ HTTP Proxy disable failed: {result2.stderr}")

            # Disable HTTPS proxy
            result3 = subprocess.run(["networksetup", "-setsecurewebproxystate", primary_service, "off"],
                                   capture_output=True, text=True, timeout=10)
            if result3.returncode == 0:
                success_count += 1
                print("✅ HTTPS Proxy disabled")
            else:
                print(f"⚠️ HTTPS Proxy disable failed: {result3.stderr}")

            # Clean up PAC file
            try:
                import os
                pac_file = os.path.expanduser("~/.warp_proxy/warp_proxy.pac")
                if os.path.exists(pac_file):
                    os.remove(pac_file)
                    print("✅ PAC file cleaned up")
            except Exception as e:
                print(f"⚠️ PAC file cleanup failed: {e}")

            # Consider success if at least one proxy type was disabled
            if success_count > 0:
                print("Proxy disabled successfully")
                return True
            else:
                print("Failed to disable any proxy settings")
                return False

        except Exception as e:
            print(f"macOS proxy disable error: {e}")
            return False

    @staticmethod
    def is_proxy_enabled():
        """Check if proxy is enabled"""
        if IS_WINDOWS:
            return ProxyManager._is_proxy_enabled_windows()
        elif IS_MACOS:
            return ProxyManager._is_proxy_enabled_macos()
        else:
            return False

    @staticmethod
    def _is_proxy_enabled_windows():
        """Check if proxy is enabled on Windows"""
        try:
            if winreg is None:
                return False

            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                               0, winreg.KEY_READ)

            proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
            winreg.CloseKey(key)

            return bool(proxy_enable)
        except:
            return False

    @staticmethod
    def _is_proxy_enabled_macos():
        """Check if proxy is enabled on macOS (PAC or manual)"""
        try:
            # Get active network service
            result = subprocess.run(["networksetup", "-listnetworkserviceorder"],
                                  capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                return False

            # Find the first active service
            services = []
            for line in result.stdout.split('\n'):
                if line.startswith('(') and ')' in line:
                    service_name = line.split(') ')[1] if ') ' in line else None
                    if service_name and service_name not in ['Bluetooth PAN', 'Thunderbolt Bridge']:
                        services.append(service_name)

            if not services:
                return False

            primary_service = services[0]

            # Check Auto Proxy (PAC) state
            result1 = subprocess.run(["networksetup", "-getautoproxyurl", primary_service],
                                  capture_output=True, text=True, timeout=10)

            if result1.returncode == 0:
                if "Enabled: Yes" in result1.stdout:
                    print("PAC proxy is enabled")
                    return True

            # Check HTTP proxy state
            result2 = subprocess.run(["networksetup", "-getwebproxy", primary_service],
                                  capture_output=True, text=True, timeout=10)

            if result2.returncode == 0:
                if "Enabled: Yes" in result2.stdout:
                    print("HTTP proxy is enabled")
                    return True

            return False

        except Exception as e:
            print(f"macOS proxy check error: {e}")
            return False


# Backward compatibility alias
ProxyManager = ProxyManager


class CertificateManager:
    """Manage mitmproxy certificate generation and installation"""

    def __init__(self):
        self.mitmproxy_dir = Path.home() / ".mitmproxy"
        # Windows uses .cer, Linux commonly uses .pem
        self.cert_file = self.mitmproxy_dir / ("mitmproxy-ca-cert.cer" if IS_WINDOWS else "mitmproxy-ca-cert.pem")

    def check_certificate_exists(self):
        """Return True if the certificate file exists"""
        return self.cert_file.exists()

    def get_certificate_path(self):
        """Return the certificate file path as a string"""
        return str(self.cert_file)

    def verify_certificate_trust_macos(self):
        """Verify if certificate is properly trusted on macOS"""
        if IS_WINDOWS or IS_LINUX:
            return True

        try:
            cert_path = self.get_certificate_path()
            if not self.check_certificate_exists():
                return False

            # Check if certificate is in keychain and trusted
            cmd = ["security", "verify-cert", "-c", cert_path]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ Certificate is properly trusted")
                return True
            else:
                print(f"⚠️ Certificate trust verification failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"Certificate verification error: {e}")
            return False

    def fix_certificate_trust_macos(self):
        """Attempt to fix certificate trust issues on macOS"""
        if IS_WINDOWS or IS_LINUX:
            return True

        try:
            cert_path = self.get_certificate_path()
            if not self.check_certificate_exists():
                print("❌ Certificate file not found")
                return False

            print("🔧 Attempting to fix certificate trust...")

            # Method 1: Remove and re-add with explicit trust
            print("Step 1: Removing existing certificate...")
            cmd_remove = ["security", "delete-certificate", "-c", "mitmproxy"]
            subprocess.run(cmd_remove, capture_output=True, text=True)

            # Method 2: Add with full trust settings
            print("Step 2: Adding certificate with full trust...")
            user_keychain = os.path.expanduser("~/Library/Keychains/login.keychain-db")

            # Import certificate
            cmd_import = ["security", "import", cert_path, "-k", user_keychain, "-A"]
            result_import = subprocess.run(cmd_import, capture_output=True, text=True)

            if result_import.returncode == 0:
                # Set trust policy explicitly for SSL
                cmd_trust = [
                    "security", "add-trusted-cert",
                    "-d", "-r", "trustRoot",
                    "-k", user_keychain,
                    cert_path
                ]
                result_trust = subprocess.run(cmd_trust, capture_output=True, text=True)

                if result_trust.returncode == 0:
                    print("✅ Certificate trust fixed successfully")
                    return True
                else:
                    print(f"❌ Trust setting failed: {result_trust.stderr}")
            else:
                print(f"❌ Certificate import failed: {result_import.stderr}")

            return False

        except Exception as e:
            print(f"Certificate trust fix error: {e}")
            return False



    def install_certificate_automatically(self):
        """Install the certificate automatically (Windows) or guide the user (Linux)"""
        try:
            cert_path = self.get_certificate_path()
            if not self.check_certificate_exists():
                print(_('certificate_not_found'))
                return False

            print(_('cert_installing'))

            if IS_WINDOWS:
                # Add the certificate to the root store with certutil
                cmd = ["certutil", "-addstore", "root", cert_path]
                result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
                if result.returncode == 0:
                    print(_('cert_installed_success'))
                    return True
                else:
                    print(_('cert_install_error').format(result.stderr))
                    return False

            elif IS_MACOS:
                # macOS: Use security command with multiple strategies

                # Strategy 1: Try to add to system keychain with trust settings
                print("Attempting to install certificate to system keychain...")
                cmd_system = [
                    "security", "add-trusted-cert",
                    "-d",  # Add to admin cert store
                    "-r", "trustRoot",  # Set trust policy
                    "-k", "/Library/Keychains/System.keychain",
                    cert_path
                ]
                result_system = subprocess.run(cmd_system, capture_output=True, text=True)

                if result_system.returncode == 0:
                    print(_('cert_installed_success'))
                    return True
                else:
                    print(f"System keychain failed: {result_system.stderr}")

                # Strategy 2: Add to login keychain with explicit trust
                print("Attempting to install certificate to login keychain...")
                user_keychain = os.path.expanduser("~/Library/Keychains/login.keychain-db")

                # First add the certificate
                cmd_add = ["security", "add-cert", "-k", user_keychain, cert_path]
                result_add = subprocess.run(cmd_add, capture_output=True, text=True)

                if result_add.returncode == 0:
                    # Then set trust policy explicitly
                    cmd_trust = [
                        "security", "add-trusted-cert",
                        "-d",  # Add to admin cert store
                        "-r", "trustRoot",  # Trust for SSL
                        "-k", user_keychain,
                        cert_path
                    ]
                    result_trust = subprocess.run(cmd_trust, capture_output=True, text=True)

                    if result_trust.returncode == 0:
                        print(_('cert_installed_success'))
                        print("✅ Certificate installed and trusted in login keychain")
                        return True
                    else:
                        print(f"Trust setting failed: {result_trust.stderr}")
                else:
                    print(f"Certificate add failed: {result_add.stderr}")

                # Strategy 3: Manual approach with user guidance
                print("Automatic installation failed. Manual installation required.")
                self._show_manual_certificate_instructions(cert_path)
                return False
            else:
                print("Linux: Please trust mitmproxy certificate manually, e.g. for Firefox/Chrome profile.")
                print(f"Certificate path: {cert_path}")
                return True

        except Exception as e:
            print(_('cert_install_error').format(str(e)))
            return False

    def _show_manual_certificate_instructions(self, cert_path):
        """Show manual certificate installation instructions for macOS"""
        print("\n" + "="*60)
        print("🔒 MANUAL CERTIFICATE INSTALLATION REQUIRED")
        print("="*60)
        print(f"Certificate location: {cert_path}")
        print("\nPlease follow these steps:")
        print("1. Open Keychain Access app (Applications → Utilities → Keychain Access)")
        print("2. Drag the certificate file to the 'System' or 'login' keychain")
        print("3. Double-click the installed certificate")
        print("4. Expand 'Trust' section")
        print("5. Set 'When using this certificate' to 'Always Trust'")
        print("6. Close the window and enter your password when prompted")
        print("\n🌐 For browsers like Chrome/Safari:")
        print("7. Restart your browser")
        print("8. The proxy should now work correctly")
        print("\n" + "="*60)


class MitmProxyManager:
    """Manage mitmproxy process lifecycle and configuration"""

    def __init__(self):
        self.process = None
        self.cmd_process_handle = None  # Track CMD window for cleanup
        self.port = 8080  # Orijinal port
        self.script_path = "warp_proxy_script.py"  # Use the main proxy script
        self.debug_mode = True
        self.cert_manager = CertificateManager()

    def start(self, parent_window=None):
        """Start the mitmproxy process"""
        try:
            if self.is_running():
                print("Mitmproxy is already running")
                return True

            # First, check if mitmproxy is properly installed
            print("🔍 Checking mitmproxy installation...")
            if not self.check_mitmproxy_installation():
                print("❌ Mitmproxy installation check failed")
                return False

            # On first run ensure the certificate exists
            if not self.cert_manager.check_certificate_exists():
                print(_('cert_creating'))

                # Run mitmproxy briefly to generate the certificate
                temp_cmd = ["mitmdump", "--set", "confdir=~/.mitmproxy", "-q"]
                try:
                    if parent_window:
                        parent_window.status_bar.showMessage(_('cert_creating'), 0)

                    popen_kwargs = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
                    if IS_WINDOWS and hasattr(subprocess, "CREATE_NO_WINDOW"):
                        popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                    temp_process = subprocess.Popen(temp_cmd, **popen_kwargs)

                    # Wait five seconds and then stop the process
                    time.sleep(5)
                    temp_process.terminate()
                    temp_process.wait(timeout=3)

                    print("✅ Certificate generation completed")

                except Exception as e:
                    print(f"❌ Certificate generation error: {e}")

                # Verify that the certificate file was created
                if not self.cert_manager.check_certificate_exists():
                    if parent_window:
                        parent_window.status_bar.showMessage(_('cert_creation_failed'), 5000)
                    return False
                else:
                    print(_('cert_created_success'))

            # Sertifika otomatik kurulumu
            if parent_window and not parent_window.account_manager.is_certificate_approved():
                print(_('cert_installing'))

                # Attempt to install the certificate automatically
                if self.cert_manager.install_certificate_automatically():
                    # Record approval if installation succeeded
                    parent_window.account_manager.set_certificate_approved(True)
                    parent_window.status_bar.showMessage(_('cert_installed_success'), 3000)

                    # On macOS additionally validate certificate trust
                    if IS_MACOS:
                        if not self.cert_manager.verify_certificate_trust_macos():
                            print("⚠️ Certificate may not be fully trusted. Manual verification recommended.")
                            parent_window.status_bar.showMessage("Certificate installed but may need manual trust setup", 5000)
                else:
                    # If automatic install fails show the manual install dialog
                    dialog_result = self.show_manual_certificate_dialog(parent_window)
                    if dialog_result:
                        # User confirmed that installation finished
                        parent_window.account_manager.set_certificate_approved(True)
                    else:
                        return False


            # Build the mitmproxy command
            cmd = [
                "mitmdump",
                "--listen-host", "127.0.0.1",  # IPv4'te dinle
                "-p", str(self.port),
                "-s", self.script_path,
                "--set", "confdir=~/.mitmproxy",
                "--set", "keep_host_header=true",    # Preserve the original host header
            ]

            print(f"Mitmproxy komutu: {' '.join(cmd)}")

            # Start process - platform-specific console handling
            if IS_WINDOWS:
                cmd_str = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in cmd)

                if self.debug_mode:
                    # Debug mode: Console window visible
                    print("Debug mode active - Mitmproxy console window will open")
                    self.cmd_process_handle = subprocess.Popen(
                        f'cmd /k "{cmd_str}"',
                        shell=True,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                else:
                    # Normal mode: Hidden console window
                    print("Normal mode - Mitmproxy will run in background")
                    self.process = subprocess.Popen(
                        cmd_str,
                        shell=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )

                # Windows start command returns immediately, so check port
                print("Starting Mitmproxy, checking port...")
                for i in range(10):  # Wait 10 seconds
                    time.sleep(1)
                    if self.is_port_open("127.0.0.1", self.port):
                        print(f"Mitmproxy started successfully - Port {self.port} is open")
                        return True
                    print(f"Checking port... ({i+1}/10)")

                print("Failed to start Mitmproxy - port did not open")
                return False
            else:
                # Linux/Mac normal startup
                if self.debug_mode:
                    print("Debug mode active - Mitmproxy will run in foreground")
                    print("🔍 TLS issues? Run diagnosis with: proxy_manager.diagnose_tls_issues()")
                    # On macOS/Linux, run in foreground for debug mode
                    self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                else:
                    print("Normal mode - Mitmproxy will run in background")
                    # Run in background but capture errors for diagnosis
                    self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                # Wait a bit and check if process is still running
                time.sleep(2)

                if self.process.poll() is None:
                    print(f"Mitmproxy started successfully (PID: {self.process.pid})")

                    # On macOS, proactively check for TLS issues if in debug mode
                    if IS_MACOS and self.debug_mode:
                        print("\n🔍 Running TLS diagnosis (macOS debug mode)...")
                        time.sleep(1)  # Give mitmproxy time to start
                        self.diagnose_tls_issues()

                    return True
                else:
                    # Process terminated, get error output
                    try:
                        stdout, stderr = self.process.communicate(timeout=5)
                        print(f"\n❌ Failed to start Mitmproxy - Process terminated")
                        print(f"\n📝 Error Details:")
                        if stderr:
                            print(f"STDERR: {stderr.strip()}")
                        if stdout:
                            print(f"STDOUT: {stdout.strip()}")

                        # Common solutions based on error patterns
                        self._suggest_mitmproxy_solutions(stderr, stdout)
                    except subprocess.TimeoutExpired:
                        print("❌ Process communication timeout")
                    return False

        except Exception as e:
            print(f"Mitmproxy startup error: {e}")
            return False

    def _suggest_mitmproxy_solutions(self, stderr, stdout):
        """Suggest solutions based on mitmproxy error output"""
        print("\n🛠️ Possible Solutions:")

        error_text = (stderr or '') + (stdout or '')
        error_lower = error_text.lower()

        # Check for common issues
        if 'permission denied' in error_lower or 'operation not permitted' in error_lower:
            print("🔒 Permission Issue:")
            print("   Try running with appropriate permissions")
            print("   Or change to a different port: proxy_manager.port = 8081")

        elif 'address already in use' in error_lower or 'port' in error_lower:
            print("🚫 Port Conflict:")
            print("   Another process is using port 8080")
            print("   Kill existing process or use different port")
            print(f"   Check with: lsof -i :8080")

        elif 'no module named' in error_lower or 'modulenotfounderror' in error_lower:
            print("📦 Missing Dependencies:")
            print("   Install required packages:")
            print("   pip3 install mitmproxy")

        elif 'command not found' in error_lower or 'no such file' in error_lower:
            print("❌ Mitmproxy Not Found:")
            print("   Install mitmproxy:")
            print("   pip3 install mitmproxy")
            print("   Or: brew install mitmproxy")

        elif 'certificate' in error_lower or 'ssl' in error_lower or 'tls' in error_lower:
            print("🔒 Certificate Issue:")
            print("   Run certificate diagnosis:")
            print("   proxy_manager.diagnose_tls_issues()")

        elif 'script' in error_lower and 'warp_proxy_script' in error_lower:
            print("📜 Script Issue:")
            print("   Check if warp_proxy_script.py exists")
            print("   Verify script has no syntax errors")

        else:
            print("🔄 General Troubleshooting:")
            print("1. Check if mitmproxy is installed: mitmdump --version")
            print("2. Try running manually: mitmdump -p 8080")
            print("3. Check system requirements and dependencies")
            print("4. Verify warp_proxy_script.py exists and is valid")

        print("\n📞 For more help, check mitmproxy documentation")

    def check_mitmproxy_installation(self):
        """Check if mitmproxy is properly installed"""
        print("\n🔍 MITMPROXY INSTALLATION CHECK")
        print("="*50)

        # Check if mitmdump command exists
        try:
            result = subprocess.run(['mitmdump', '--version'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"✅ Mitmproxy installed: {result.stdout.strip()}")
            else:
                print(f"❌ Mitmproxy version check failed: {result.stderr}")
                return False
        except FileNotFoundError:
            print("❌ Mitmproxy not found in PATH")
            print("\n📝 Installation commands:")
            print("   pip3 install mitmproxy")
            print("   or: brew install mitmproxy")
            return False
        except subprocess.TimeoutExpired:
            print("❌ Mitmproxy version check timed out")
            return False

        # Check if warp_proxy_script.py exists
        if os.path.exists(self.script_path):
            print(f"✅ Proxy script found: {self.script_path}")
        else:
            print(f"❌ Proxy script missing: {self.script_path}")
            return False

        # Check port availability
        if not self.is_port_open("127.0.0.1", self.port):
            print(f"✅ Port {self.port} is available")
        else:
            print(f"⚠️ Port {self.port} is already in use")
            print("   Kill the process using this port or choose a different port")

        return True

    def stop(self):
        """Mitmproxy'yi durdur"""
        try:
            # Close CMD debug window first (Windows only)
            if IS_WINDOWS and self.cmd_process_handle:
                try:
                    print("Closing CMD debug window...")
                    subprocess.call(
                        ['taskkill', '/F', '/T', '/PID', str(self.cmd_process_handle.pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    print("CMD debug window closed")
                except Exception as e:
                    print(f"CMD window close warning: {e}")
                finally:
                    self.cmd_process_handle = None
            
            if self.process and self.process.poll() is None:
                self.process.terminate()
                self.process.wait(timeout=10)
                print("Mitmproxy durduruldu")
                return True

            # If no process reference is stored, find by PID and terminate
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'mitmdump' in proc.info['name'] and str(self.port) in ' '.join(proc.info['cmdline']):
                        proc.terminate()
                        proc.wait(timeout=10)
                        print(f"Mitmproxy durduruldu (PID: {proc.info['pid']})")
                        return True
                except:
                    continue

            return True
        except Exception as e:
            print(f"Mitmproxy shutdown error: {e}")
            return False

    def is_running(self):
        """Return True if the mitmproxy process is running"""
        try:
            if self.process and self.process.poll() is None:
                return True

            # PID ile kontrol et
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'mitmdump' in proc.info['name'] and str(self.port) in ' '.join(proc.info['cmdline']):
                        return True
                except:
                    continue
            return False
        except:
            return False

    def get_proxy_url(self):
        """Return the local proxy URL"""
        return f"127.0.0.1:{self.port}"

    def diagnose_tls_issues(self):
        """Diagnose TLS handshake issues and suggest solutions"""
        print("\n" + "🔍" + " TLS HANDSHAKE DIAGNOSIS" + "\n" + "="*50)

        # Check certificate existence
        if not self.cert_manager.check_certificate_exists():
            print("❌ Certificate not found")
            print("📝 Solution: Restart mitmproxy to generate certificate")
            return False

        print("✅ Certificate file exists")

        if IS_MACOS:
            # macOS specific checks
            print("\n🍎 macOS Certificate Trust Check:")

            if self.cert_manager.verify_certificate_trust_macos():
                print("✅ Certificate is trusted by system")
            else:
                print("❌ Certificate is NOT trusted by system")
                print("\n🛠️ Attempting automatic fix...")

                if self.cert_manager.fix_certificate_trust_macos():
                    print("✅ Automatic fix successful!")
                else:
                    print("❌ Automatic fix failed")
                    print("\n📝 Manual Fix Required:")
                    self.cert_manager._show_manual_certificate_instructions(self.cert_manager.get_certificate_path())
                    return False

        # Additional checks
        print("\n🌐 Browser Recommendations:")
        print("1. Chrome: Restart browser after certificate installation")
        print("2. Safari: May require manual certificate approval in Keychain Access")
        print("3. Firefox: Uses its own certificate store - may need separate installation")

        return True

    def is_port_open(self, host, port):
        """Check whether the given host/port is reachable"""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False

    def show_manual_certificate_dialog(self, parent_window):
        """Display the manual certificate installation dialog"""
        try:
            dialog = ManualCertificateDialog(self.cert_manager.get_certificate_path(), parent_window)
            return dialog.exec_() == QDialog.Accepted
        except Exception as e:
            print(f"Manual certificate dialog error: {e}")
            return False


class ManualCertificateDialog(QDialog):
    """Dialog guiding the user through manual certificate installation"""

    def __init__(self, cert_path, parent=None):
        super().__init__(parent)
        self.cert_path = cert_path
        self.setWindowTitle(_('cert_manual_title'))
        self.setGeometry(300, 300, 650, 550)
        self.setModal(True)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title label
        title = QLabel(_('cert_manual_title'))
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #d32f2f; margin-bottom: 10px;")
        layout.addWidget(title)

        # Instruction text
        explanation = QLabel(_('cert_manual_explanation'))
        explanation.setWordWrap(True)
        explanation.setStyleSheet("background: #fff3cd; padding: 15px; border-radius: 8px; border: 1px solid #ffeaa7;")
        layout.addWidget(explanation)

        # Certificate path label and display
        path_label = QLabel(_('cert_manual_path'))
        path_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(path_label)

        path_display = QLabel(self.cert_path)
        path_display.setStyleSheet("""
            background: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            border: 1px solid #ddd;
            font-family: 'Courier New', monospace;
            font-size: 11px;
        """)
        path_display.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(path_display)

        # Installation steps
        steps_label = QLabel(_('cert_manual_steps'))
        steps_label.setWordWrap(True)
        steps_label.setStyleSheet("background: white; padding: 15px; border-radius: 8px; border: 1px solid #ddd;")
        layout.addWidget(steps_label)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # Button to open the certificate folder directly
        self.open_folder_button = QPushButton(_('cert_open_folder'))
        self.open_folder_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.open_folder_button.clicked.connect(self.open_certificate_folder)

        # Button confirming certificate install completion
        self.completed_button = QPushButton(_('cert_manual_complete'))
        self.completed_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.completed_button.clicked.connect(self.accept)

        # Cancel button
        cancel_button = QPushButton(_('cancel'))
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.open_folder_button)
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(self.completed_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def open_certificate_folder(self):
        """Open certificate folder in file explorer"""
        try:
            import os
            cert_dir = os.path.dirname(self.cert_path)
            if os.path.exists(cert_dir):
                if IS_WINDOWS:
                    subprocess.Popen(['explorer', cert_dir])
                elif IS_MACOS:
                    subprocess.Popen(['open', cert_dir])
                else:
                    subprocess.Popen(['xdg-open', cert_dir])
            else:
                QMessageBox.warning(self, _('error'), _('certificate_not_found'))
        except Exception as e:
            QMessageBox.warning(self, _('error'), _('file_open_error').format(str(e)))


class TokenWorker(QThread):
    """Refresh a single account token in the background"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)  # success, message
    error = pyqtSignal(str)

    def __init__(self, email, account_data, proxy_enabled=False):
        super().__init__()
        self.email = email
        self.account_data = account_data
        self.account_manager = AccountManager()
        self.proxy_enabled = proxy_enabled

    def run(self):
        try:
            self.progress.emit(f"Refreshing token for {self.email}")

            if self.refresh_token():
                self.account_manager.update_account_health(self.email, 'healthy')
                self.finished.emit(True, f"Token refreshed successfully for {self.email}")
            else:
                self.account_manager.update_account_health(self.email, 'unhealthy')
                self.finished.emit(False, f"Token refresh failed for {self.email}")

        except Exception as e:
            self.error.emit(f"Token refresh error: {str(e)}")

    def refresh_token(self):
        """Refresh the Firebase token for this account"""
        try:
            refresh_token = self.account_data['stsTokenManager']['refreshToken']
            api_key = self.account_data['apiKey']

            url = f"https://securetoken.googleapis.com/v1/token?key={api_key}"
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'WarpAccountManager/1.0'
            }
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token
            }

            # Connect without using a proxy
            proxies = {'http': None, 'https': None} if self.proxy_enabled else None
            response = requests.post(url, json=data, headers=headers, timeout=30,
                                   verify=not self.proxy_enabled, proxies=proxies)

            if response.status_code == 200:
                token_data = response.json()
                new_token_data = {
                    'accessToken': token_data['access_token'],
                    'refreshToken': token_data['refresh_token'],
                    'expirationTime': int(time.time() * 1000) + (int(token_data['expires_in']) * 1000)
                }

                return self.account_manager.update_account_token(self.email, new_token_data)
            return False
        except Exception as e:
            print(f"Token refresh error: {e}")
            return False


class TokenRefreshWorker(QThread):
    """Refresh tokens and fetch limit info for many accounts in the background"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, accounts, proxy_enabled=False):
        super().__init__()
        self.accounts = accounts
        self.account_manager = AccountManager()
        self.proxy_enabled = proxy_enabled

    def run(self):
        results = []
        total_accounts = len(self.accounts)

        for i, (email, account_json, health_status) in enumerate(self.accounts):
            try:
                self.progress.emit(int((i / total_accounts) * 100), _('processing_account', email))

                # Skip banned accounts
                if health_status == _('status_banned_key'):
                    self.account_manager.update_account_limit_info(email, _('status_na'))
                    results.append((email, _('status_banned'), _('status_na')))
                    continue

                account_data = json.loads(account_json)

                # Check token expiration
                expiration_time = account_data['stsTokenManager']['expirationTime']
                current_time = int(time.time() * 1000)

                if current_time >= expiration_time:
                    # Token expired, attempt a refresh
                    self.progress.emit(int((i / total_accounts) * 100), _('refreshing_token', email))
                    if not self.refresh_token(email, account_data):
                        # Token refresh failed; mark account unhealthy
                        self.account_manager.update_account_health(email, _('status_unhealthy'))
                        self.account_manager.update_account_limit_info(email, _('status_na'))
                        results.append((email, _('token_refresh_failed', email), _('status_na')))
                        continue

                    # Pull updated account data from the database
                    updated_accounts = self.account_manager.get_accounts()
                    for updated_email, updated_json in updated_accounts:
                        if updated_email == email:
                            account_data = json.loads(updated_json)
                            break

                # Fetch limit information
                limit_info = self.get_limit_info(account_data)
                if limit_info:
                    used = limit_info.get('requestsUsedSinceLastRefresh', 0)
                    total = limit_info.get('requestLimit', 0)
                    limit_text = f"{used}/{total}"
                    # Successful update: mark healthy and store limit data
                    self.account_manager.update_account_health(email, _('status_healthy'))
                    self.account_manager.update_account_limit_info(email, limit_text)
                    results.append((email, _('success'), limit_text))
                else:
                    # Limit information unavailable; mark unhealthy
                    self.account_manager.update_account_health(email, _('status_unhealthy'))
                    self.account_manager.update_account_limit_info(email, _('status_na'))
                    results.append((email, _('limit_info_failed'), _('status_na')))

            except Exception as e:
                self.account_manager.update_account_limit_info(email, _('status_na'))
                results.append((email, f"{_('error')}: {str(e)}", _('status_na')))

        self.finished.emit(results)

    def refresh_token(self, email, account_data):
        """Refresh the Firebase token for the given account"""
        try:
            refresh_token = account_data['stsTokenManager']['refreshToken']
            api_key = account_data['apiKey']

            url = f"https://securetoken.googleapis.com/v1/token?key={api_key}"
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'WarpAccountManager/1.0'  # Identify requests originating from the manager
            }
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token
            }

            # Connect without using a proxy when not required
            proxies = {'http': None, 'https': None} if self.proxy_enabled else None
            response = requests.post(url, json=data, headers=headers, timeout=30,
                                   verify=not self.proxy_enabled, proxies=proxies)

            if response.status_code == 200:
                token_data = response.json()
                new_token_data = {
                    'accessToken': token_data['access_token'],
                    'refreshToken': token_data['refresh_token'],
                    'expirationTime': int(time.time() * 1000) + (int(token_data['expires_in']) * 1000)
                }

                return self.account_manager.update_account_token(email, new_token_data)
            return False
        except Exception as e:
            print(f"Token refresh error: {e}")
            return False

    def get_limit_info(self, account_data):
        """Warp API'den limit bilgilerini getir"""
        try:
            access_token = account_data['stsTokenManager']['accessToken']

            # Get dynamic OS information
            os_info = get_os_info()

            url = "https://app.warp.dev/graphql/v2?op=GetRequestLimitInfo"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}',
                'X-Warp-Client-Version': 'v0.2025.08.27.08.11.stable_04',
                'X-Warp-Os-Category': os_info['category'],
                'X-Warp-Os-Name': os_info['name'],
                'X-Warp-Os-Version': os_info['version'],
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'X-Warp-Manager-Request': 'true'  # Identify request as originating from our application
            }

            query = """
            query GetRequestLimitInfo($requestContext: RequestContext!) {
              user(requestContext: $requestContext) {
                __typename
                ... on UserOutput {
                  user {
                    requestLimitInfo {
                      isUnlimited
                      nextRefreshTime
                      requestLimit
                      requestsUsedSinceLastRefresh
                      requestLimitRefreshDuration
                      isUnlimitedAutosuggestions
                      acceptedAutosuggestionsLimit
                      acceptedAutosuggestionsSinceLastRefresh
                      isUnlimitedVoice
                      voiceRequestLimit
                      voiceRequestsUsedSinceLastRefresh
                      voiceTokenLimit
                      voiceTokensUsedSinceLastRefresh
                      isUnlimitedCodebaseIndices
                      maxCodebaseIndices
                      maxFilesPerRepo
                      embeddingGenerationBatchSize
                    }
                  }
                }
                ... on UserFacingError {
                  error {
                    __typename
                    ... on SharedObjectsLimitExceeded {
                      limit
                      objectType
                      message
                    }
                    ... on PersonalObjectsLimitExceeded {
                      limit
                      objectType
                      message
                    }
                    ... on AccountDelinquencyError {
                      message
                    }
                    ... on GenericStringObjectUniqueKeyConflict {
                      message
                    }
                  }
                  responseContext {
                    serverVersion
                  }
                }
              }
            }
            """

            payload = {
                "query": query,
                "variables": {
                    "requestContext": {
                        "clientContext": {
                            "version": "v0.2025.08.27.08.11.stable_04"
                        },
                        "osContext": {
                            "category": os_info['category'],
                            "linuxKernelVersion": None,
                            "name": os_info['category'],
                            "version": os_info['version']
                        }
                    }
                },
                "operationName": "GetRequestLimitInfo"
            }

            # Connect without using a proxy
            proxies = {'http': None, 'https': None} if self.proxy_enabled else None
            response = requests.post(url, headers=headers, json=payload, timeout=30,
                                   verify=not self.proxy_enabled, proxies=proxies)

            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'user' in data['data']:
                    user_data = data['data']['user']
                    if user_data.get('__typename') == 'UserOutput':
                        return user_data['user']['requestLimitInfo']
            return None
        except Exception as e:
            print(f"Limit information retrieval error: {e}")
            return None


class AddAccountDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_('add_account_title'))
        self.setGeometry(200, 200, 800, 600)
        self.init_ui()

    def init_ui(self):
        # Primary layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Create tab widget containing manual/automatic tabs
        self.tab_widget = QTabWidget()

        # Manual entry tab
        manual_tab = self.create_manual_tab()
        self.tab_widget.addTab(manual_tab, _('tab_manual'))

        # Automatic entry tab
        auto_tab = self.create_auto_tab()
        self.tab_widget.addTab(auto_tab, _('tab_auto'))

        main_layout.addWidget(self.tab_widget)

        # Shared buttons for both tabs
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        # Button linking to account creation page (left side)
        self.create_account_button = QPushButton(_('create_account'))
        self.create_account_button.setMinimumHeight(28)
        self.create_account_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.create_account_button.clicked.connect(self.open_account_creation_page)

        self.add_button = QPushButton(_('add'))
        self.add_button.setMinimumHeight(28)
        self.add_button.clicked.connect(self.accept)

        self.cancel_button = QPushButton(_('cancel'))
        self.cancel_button.setMinimumHeight(28)
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.create_account_button)
        button_layout.addStretch()
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.cancel_button)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def create_manual_tab(self):
        """Create the manual JSON entry tab"""
        tab_widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Section title
        title_label = QLabel(_('manual_method_title'))
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title_label)

        # Main horizontal layout
        content_layout = QHBoxLayout()
        content_layout.setSpacing(12)

        # Left panel with input form
        left_panel = QVBoxLayout()
        left_panel.setSpacing(8)

        # Instruction label
        instruction_label = QLabel(_('add_account_instruction'))
        instruction_label.setFont(QFont("Arial", 10))
        left_panel.addWidget(instruction_label)

        # JSON text input
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(_('add_account_placeholder'))
        left_panel.addWidget(self.text_edit)

        # Toggle button for info panel
        self.info_button = QPushButton(_('how_to_get_json'))
        self.info_button.setMaximumWidth(220)
        self.info_button.clicked.connect(self.toggle_info_panel)
        left_panel.addWidget(self.info_button)

        content_layout.addLayout(left_panel, 1)

        # Right panel (info panel) hidden by default
        self.info_panel = self.create_info_panel()
        self.info_panel.hide()
        self.info_panel_visible = False
        content_layout.addWidget(self.info_panel, 1)

        layout.addLayout(content_layout)
        tab_widget.setLayout(layout)
        return tab_widget

    def create_auto_tab(self):
        """Create the Chrome extension auto-add tab"""
        tab_widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Section title
        title_label = QLabel(_('auto_method_title'))
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title_label)

        # Scroll area containing extension instructions
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_layout.setContentsMargins(12, 12, 12, 12)
        scroll_layout.setSpacing(16)

        # Chrome extension description
        chrome_title = QLabel(_('chrome_extension_title'))
        chrome_title.setFont(QFont("Arial", 11, QFont.Bold))
        scroll_layout.addWidget(chrome_title)

        chrome_desc = QLabel(_('chrome_extension_description'))
        chrome_desc.setWordWrap(True)
        chrome_desc.setStyleSheet("QLabel { color: #666; }")
        scroll_layout.addWidget(chrome_desc)

        # Step-by-step guide container
        steps_widget = QWidget()
        steps_widget.setStyleSheet("QWidget { background-color: #151937; border: 1px solid #2d3b8f; border-radius: 8px; padding: 12px; }")
        steps_layout = QVBoxLayout()
        steps_layout.setSpacing(8)

        steps = [
            _('chrome_extension_step_1'),
            _('chrome_extension_step_2'),
            _('chrome_extension_step_3'),
            _('chrome_extension_step_4')
        ]

        for step in steps:
            step_label = QLabel(step)
            step_label.setWordWrap(True)
            step_label.setStyleSheet("QLabel { margin: 4px 0; }")
            steps_layout.addWidget(step_label)

        steps_widget.setLayout(steps_layout)
        scroll_layout.addWidget(steps_widget)

        scroll_layout.addStretch()
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)

        layout.addWidget(scroll_area)
        tab_widget.setLayout(layout)
        return tab_widget

    def create_info_panel(self):
        """Construct the information panel"""
        panel = QWidget()
        panel.setMaximumWidth(400)
        panel.setStyleSheet("QWidget { background-color: #151937; border: 1px solid #2d3b8f; border-radius: 8px; padding: 8px; }")

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Info panel title
        title = QLabel(_('json_info_title'))
        title.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(title)

        # Steps explaining manual JSON extraction
        steps_text = f"""
{_('step_1')}<br><br>
{_('step_2')}<br><br>
{_('step_3')}<br><br>
{_('step_4')}<br><br>
{_('step_5')}<br><br>
{_('step_6')}<br><br>
{_('step_7')}
        """

        steps_label = QLabel(steps_text)
        steps_label.setWordWrap(True)
        steps_label.setStyleSheet("QLabel { background-color: #0f1438; padding: 8px; border-radius: 4px; color: #c7d2fe; }")
        layout.addWidget(steps_label)

        # JavaScript kodu (gizli, sadece kopyala butonu)
        self.javascript_code = """(async () => {
  const request = indexedDB.open("firebaseLocalStorageDb");

  request.onsuccess = function (event) {
    const db = event.target.result;
    const tx = db.transaction("firebaseLocalStorage", "readonly");
    const store = tx.objectStore("firebaseLocalStorage");

    const getAllReq = store.getAll();

    getAllReq.onsuccess = function () {
      const results = getAllReq.result;

      // get the first record's value
      const firstValue = results[0]?.value;
      console.log("Value (object):", firstValue);

      // convert to JSON string
      const valueString = JSON.stringify(firstValue, null, 2);

      // add a button to copy the value
      const btn = document.createElement("button");
      btn.innerText = "-> Copy JSON <--";
      btn.style.position = "fixed";
      btn.style.top = "20px";
      btn.style.right = "20px";
      btn.style.zIndex = 9999;
      btn.onclick = () => {
        navigator.clipboard.writeText(valueString).then(() => {
          alert("Copied!");
        });
      };
      document.body.appendChild(btn);
    };
  };
})();"""

        # Kodu kopyala butonu
        self.copy_button = QPushButton(_('copy_javascript'))
        self.copy_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; border: none; padding: 8px; border-radius: 4px; font-weight: bold; }")
        self.copy_button.clicked.connect(self.copy_javascript_code)
        layout.addWidget(self.copy_button)

        layout.addStretch()
        panel.setLayout(layout)
        return panel

    def toggle_info_panel(self):
        """Toggle visibility of the information panel"""
        self.info_panel_visible = not self.info_panel_visible

        if self.info_panel_visible:
            self.info_panel.show()
            self.info_button.setText(_('how_to_get_json_close'))
            # Expand dialog width when showing info panel
            self.resize(1100, 500)
        else:
            self.info_panel.hide()
            self.info_button.setText(_('how_to_get_json'))
            # Restore original dialog width
            self.resize(700, 500)

    def copy_javascript_code(self):
        """Copy the helper JavaScript to the clipboard"""
        try:
            from PyQt5.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(self.javascript_code)

            # Temporarily update button text
            original_text = self.copy_button.text()
            self.copy_button.setText(_('copied'))

            # Restore original button text after two seconds
            QTimer.singleShot(2000, lambda: self.copy_button.setText(original_text))

        except Exception as e:
            self.copy_button.setText(_('copy_error'))
            QTimer.singleShot(2000, lambda: self.copy_button.setText(_('copy_javascript')))

    def open_account_creation_page(self):
        """Open the Warp account creation page"""
        import webbrowser
        webbrowser.open("https://app.warp.dev/login/")

    def get_json_data(self):
        return self.text_edit.toPlainText().strip()


class HelpDialog(QDialog):
    """Dialog presenting guidance and usage information"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_('help_title'))
        self.setGeometry(250, 250, 700, 550)
        self.setModal(True)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Dialog title
        title = QLabel(_('help_title'))
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color: #2196F3; margin-bottom: 15px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Scroll area with the help content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")

        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(20)

        # Section 1: What does it do?
        section1 = self.create_section(
            _('help_what_is'),
            _('help_what_is_content')
        )
        content_layout.addWidget(section1)

        # Section 2: How does it work?
        section2 = self.create_section(
            _('help_how_works'),
            _('help_how_works_content')
        )
        content_layout.addWidget(section2)

        # Section 3: How to use it?
        section3 = self.create_section(
            _('help_how_to_use'),
            _('help_how_to_use_content')
        )
        content_layout.addWidget(section3)

        content_widget.setLayout(content_layout)
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

        # Close button
        close_button = QPushButton(_('close'))
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 30px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        close_button.clicked.connect(self.accept)

        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_layout.addWidget(close_button)
        close_layout.addStretch()
        layout.addLayout(close_layout)

        self.setLayout(layout)

    def create_section(self, title, content):
        """Create a help section widget"""
        section_widget = QWidget()
        section_widget.setStyleSheet("QWidget { background-color: #151937; border: 1px solid #2d3b8f; border-radius: 8px; padding: 15px; }")

        section_layout = QVBoxLayout()
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(10)

        # Section header label
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        title_label.setStyleSheet("color: #a5b4fc; margin-bottom: 5px;")
        section_layout.addWidget(title_label)

        # Section content
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setStyleSheet("color: #c7d2fe; line-height: 1.4;")
        section_layout.addWidget(content_label)

        section_widget.setLayout(section_layout)
        return section_widget


class MainWindow(QMainWindow):
    # Signal emitted when an account is added via the bridge
    bridge_account_added = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.account_manager = AccountManager()
        self.proxy_manager = MitmProxyManager()
        self.proxy_enabled = False

        # Clear active account if proxy is disabled on Windows
        if IS_WINDOWS and ProxyManager and not ProxyManager.is_proxy_enabled():
            self.account_manager.clear_active_account()

        # Connect bridge signal to update slot
        self.bridge_account_added.connect(self.refresh_table_after_bridge_add)

        self.init_ui()
        self.load_accounts()

        # Configure and start bridge components after the UI loads
        self.setup_bridge_system()

        # Timer for checking proxy status
        self.proxy_timer = QTimer()
        self.proxy_timer.timeout.connect(self.check_proxy_status)
        self.proxy_timer.start(5000)  # Check every 5 seconds

        # Timer for checking ban notifications
        self.ban_timer = QTimer()
        self.ban_timer.timeout.connect(self.check_ban_notifications)
        self.ban_timer.start(1000)  # Check every second

        # Timer for automatic token renewal
        self.token_renewal_timer = QTimer()
        self.token_renewal_timer.timeout.connect(self.auto_renew_tokens)
        self.token_renewal_timer.start(60000)  # Check every 60 seconds (60000 ms)

        # Timer for refreshing the active account
        self.active_account_refresh_timer = QTimer()
        self.active_account_refresh_timer.timeout.connect(self.refresh_active_account)
        self.active_account_refresh_timer.start(60000)  # Refresh every 60 seconds

        # Timer for resetting the status message
        self.status_reset_timer = QTimer()
        self.status_reset_timer.setSingleShot(True)
        self.status_reset_timer.timeout.connect(self.reset_status_message)

        # Perform an initial token check immediately
        QTimer.singleShot(0, self.auto_renew_tokens)

        # Placeholders for background token workers
        self.token_worker = None
        self.token_progress_dialog = None

    def setup_bridge_system(self):
        """Configure the bridge system and start its server"""
        try:
            print("🌉 Starting bridge system...")

            # On Windows ensure bridge configuration is applied
            if IS_WINDOWS and BridgeConfig is not None:
                bridge_config = BridgeConfig()
                if not bridge_config.check_configuration():
                    print("⚙️  Configuring bridge...")
                    bridge_config.setup_bridge_config()

            # Start bridge server (refresh table via callback)
            self.bridge_server = WarpBridgeServer(
                self.account_manager,
                on_account_added=self.on_account_added_via_bridge
            )
            if self.bridge_server.start():
                print("✅ Bridge system ready!")
            else:
                print("❌ Bridge server failed to start!")

        except Exception as e:
            print(f"❌ Bridge system error: {e}")
            # Continue running even if bridge setup fails
            self.bridge_server = None

    def init_ui(self):
        self.setWindowTitle(_('app_title'))
        self.setGeometry(100, 100, 900, 650)  # Slightly larger default window
        self.setMinimumSize(750, 500)  # Enforce minimum window size

        # Add status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Spacer to help center-align status messages
        spacer_label = QLabel("  ")  # Blank padding label
        self.status_bar.addWidget(spacer_label)

       
        self.indokq_label = QLabel('<a href="https://github.com/Indokq" style="color: #2196F3; text-decoration: none; font-weight: bold;">https://github.com/Indokq</a>')
        self.indokq_label.setOpenExternalLinks(True)
        self.indokq_label.setStyleSheet("QLabel { padding: 2px 8px; }")
        self.status_bar.addPermanentWidget(self.indokq_label)

        # Default status bar message
        debug_mode = os.path.exists("debug.txt")
        if debug_mode:
            self.status_bar.showMessage(_('default_status_debug'))
        else:
            self.status_bar.showMessage(_('default_status'))

        # Main container widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Root layout with generous spacing
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)  # Wide margins
        layout.setSpacing(12)  # Extra spacing between elements

        # Top action row
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)  # Provide space between buttons

        # Proxy buttons (start remains hidden, functionality merged into account controls)
        self.proxy_start_button = QPushButton(_('proxy_start'))
        self.proxy_start_button.setObjectName("StartButton")
        self.proxy_start_button.setMinimumHeight(36)
        self.proxy_start_button.clicked.connect(self.start_proxy)
        self.proxy_start_button.setVisible(False)

        self.proxy_stop_button = QPushButton(_('proxy_stop'))
        self.proxy_stop_button.setObjectName("StopButton")
        self.proxy_stop_button.setMinimumHeight(36)
        self.proxy_stop_button.clicked.connect(self.stop_proxy)
        self.proxy_stop_button.setVisible(False)

        # Additional primary buttons
        self.add_account_button = QPushButton(_('add_account'))
        self.add_account_button.setObjectName("AddButton")
        self.add_account_button.setMinimumHeight(36)
        self.add_account_button.clicked.connect(self.add_account)

        self.refresh_limits_button = QPushButton(_('refresh_limits'))
        self.refresh_limits_button.setObjectName("RefreshButton")
        self.refresh_limits_button.setMinimumHeight(36)
        self.refresh_limits_button.clicked.connect(self.refresh_limits)

        button_layout.addWidget(self.proxy_stop_button)
        button_layout.addWidget(self.add_account_button)
        button_layout.addWidget(self.refresh_limits_button)
        button_layout.addStretch()

        # Language selector
        self.language_combo = QComboBox()
        self.language_combo.addItems(['ID', 'EN'])
        self.language_combo.setCurrentText('ID' if get_language_manager().get_current_language() == 'id' else 'EN')
        self.language_combo.setFixedWidth(65)
        self.language_combo.setFixedHeight(36)
        self.language_combo.setStyleSheet("""
            QComboBox {
                background-color: #1e2555;
                color: #c7d2fe;
                border: 1px solid #2d3b8f;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 10pt;
                font-weight: 600;
                text-align: center;
            }
            QComboBox:hover {
                background-color: #2d3b8f;
                color: #e0e7ff;
                border-color: #4c51bf;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                width: 10px;
                height: 10px;
                margin-right: 4px;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1f4d;
                border: 1px solid #2d3b8f;
                border-radius: 6px;
                selection-background-color: #4c51bf;
                selection-color: #ffffff;
                color: #c7d2fe;
                font-weight: 600;
                padding: 4px;
            }
        """)
        self.language_combo.currentTextChanged.connect(self.change_language)
        button_layout.addWidget(self.language_combo)

        # Help button on the right
        self.help_button = QPushButton(_('help'))
        self.help_button.setFixedHeight(36)
        self.help_button.setStyleSheet("""
            QPushButton {
                background-color: #1e2555;
                color: #c7d2fe;
                border: 1px solid #2d3b8f;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 10pt;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2d3b8f;
                color: #e0e7ff;
                border-color: #4c51bf;
            }
        """)
        self.help_button.setToolTip(_('help_title'))
        self.help_button.clicked.connect(self.show_help_dialog)
        button_layout.addWidget(self.help_button)

        layout.addLayout(button_layout)

        # Accounts table setup
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([_('current'), _('email'), _('status'), _('limit')])

        # Styling for cleaner table appearance
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)  # Slightly taller rows for readability
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)

        # Modern dark theme table styles removed - using style.qss instead

        # Enable context menu for table rows
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        # Configure header resizing behavior
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # Fixed width for status button column
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Stretch email column
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Size status column to contents
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Size limit column to contents
        header.resizeSection(0, 90)  # Smaller width for centered button
        header.setFixedHeight(40)  # Taller header for modern look

        layout.addWidget(self.table)

        central_widget.setLayout(layout)

    def load_accounts(self, preserve_limits=False):
        """Populate the table with account data"""
        accounts = self.account_manager.get_accounts_with_health_and_limits()

        self.table.setRowCount(len(accounts))
        active_account = self.account_manager.get_active_account()

        for row, (email, account_json, health_status, limit_info) in enumerate(accounts):
            # Activation button rendered in column 0
            activation_button = QPushButton()
            activation_button.setFixedSize(70, 28)
            activation_button.setStyleSheet("""
                QPushButton {
                    border: 1px solid #2d3b8f;
                    border-radius: 6px;
                    font-weight: 600;
                    font-size: 9pt;
                    text-align: center;
                    padding: 6px 10px;
                    background-color: #1e2555;
                    color: #c7d2fe;
                }
                QPushButton:hover {
                    background-color: #2d3b8f;
                    border-color: #4c51bf;
                }
                QPushButton:pressed {
                    background-color: #1a1f4d;
                }
            """)

            # Determine button styling based on status
            is_active = (email == active_account)
            is_banned = (health_status == _('status_banned_key'))

            if is_banned:
                activation_button.setText(_('button_banned'))
                activation_button.setStyleSheet(activation_button.styleSheet() + """
                    QPushButton {
                        background-color: #151937;
                        color: #64748b;
                        border-color: #1e2555;
                        font-size: 9pt;
                    }
                """)
                activation_button.setEnabled(False)
            elif is_active:
                activation_button.setText(_('button_stop'))
                activation_button.setStyleSheet(activation_button.styleSheet() + """
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                   stop:0 #ef4444, stop:1 #dc2626);
                        color: #ffffff;
                        border: none;
                        font-size: 9pt;
                        font-weight: 700;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                   stop:0 #f87171, stop:1 #ef4444);
                    }
                """)
            else:
                activation_button.setText(_('button_start'))
                activation_button.setStyleSheet(activation_button.styleSheet() + """
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                   stop:0 #10b981, stop:1 #059669);
                        color: #ffffff;
                        border: none;
                        font-size: 9pt;
                        font-weight: 700;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                   stop:0 #34d399, stop:1 #10b981);
                    }
                """)

            # Connect button click handler
            activation_button.clicked.connect(lambda checked, e=email: self.toggle_account_activation(e))
            self.table.setCellWidget(row, 0, activation_button)

            # Email column (1)
            email_item = QTableWidgetItem(email)
            self.table.setItem(row, 1, email_item)

            # Status column (2)
            try:
                # Check whether account is banned
                if health_status == _('status_banned_key'):
                    status = _('status_banned')
                else:
                    account_data = json.loads(account_json)
                    expiration_time = account_data['stsTokenManager']['expirationTime']
                    current_time = int(time.time() * 1000)

                    if current_time >= expiration_time:
                        status = _('status_token_expired')
                    else:
                        status = _('status_active')

                    # Append proxy-active marker for selected account
                    if email == active_account:
                        status += _('status_proxy_active')

            except:
                status = _('status_error')

            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 2, status_item)

            # Limit column (3) using stored info (defaults to "Not Updated")
            limit_item = QTableWidgetItem(limit_info or _('status_not_updated'))
            limit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 3, limit_item)

            # Determine row styling based on account state
            from PyQt5.QtGui import QColor, QBrush

            if health_status == 'banned':
                # Banned account: darker background with muted text
                bg_color = QColor(30, 37, 85, 40)  # Very subtle dark overlay
                text_color = QColor(148, 163, 184)  # Lighter gray for better readability
            elif email == active_account:
                # Active account: blue highlight
                bg_color = QColor(59, 130, 246, 60)  # blue-500 with moderate opacity
                text_color = QColor(255, 255, 255)  # Pure white for contrast
            elif health_status == 'unhealthy':
                # Unhealthy account: red highlight
                bg_color = QColor(239, 68, 68, 60)  # red-500 with moderate opacity
                text_color = QColor(254, 226, 226)  # Light red tint
            else:
                # Default state: transparent background with high-contrast text
                bg_color = QColor(255, 255, 255, 0)  # transparent
                text_color = QColor(224, 231, 255)  # Bright text for readability

            # Apply styling to all data columns (skip button column)
            for col in range(1, 4):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(bg_color)
                    item.setForeground(QBrush(text_color))

    def toggle_account_activation(self, email):
        """Toggle account activation and start proxy if needed"""

        # Block activation when account is banned
        accounts_with_health = self.account_manager.get_accounts_with_health()
        for acc_email, _, acc_health in accounts_with_health:
            if acc_email == email and acc_health == 'banned':
                self.show_status_message(f"{email} is banned and cannot be activated", 5000)
                return

        # Compare with currently active account
        active_account = self.account_manager.get_active_account()

        if email == active_account and self.proxy_enabled:
            # Account already active; deactivate and stop proxy
            self.stop_proxy()
        else:
            # Activate account, starting proxy if necessary
            if not self.proxy_enabled:
                # Start proxy first
                self.show_status_message(f"Starting proxy and activating {email}...", 2000)
                if self.start_proxy_and_activate_account(email):
                    return  # Success handled in start method
                else:
                    return  # Failure already messaged
            else:
                # Proxy already running; activate account directly
                self.activate_account(email)

    def show_context_menu(self, position):
        """Show context menu for the table"""
        item = self.table.itemAt(position)
        if item is None:
            return

        row = item.row()
        email_item = self.table.item(row, 1)  # Email is in column 1
        if not email_item:
            return

        email = email_item.text()

        # Determine account health status
        accounts_with_health = self.account_manager.get_accounts_with_health()
        health_status = None
        for acc_email, _, acc_health in accounts_with_health:
            if acc_email == email:
                health_status = acc_health
                break

        # Create context menu actions
        menu = QMenu(self)

        # Add activate/deactivate actions as appropriate
        if self.proxy_enabled:
            active_account = self.account_manager.get_active_account()
            if email == active_account:
                deactivate_action = QAction("🔴 Deactivate", self)
                deactivate_action.triggered.connect(lambda: self.deactivate_account(email))
                menu.addAction(deactivate_action)
            else:
                if health_status != 'banned':
                    activate_action = QAction("🟢 Activate", self)
                    activate_action.triggered.connect(lambda: self.activate_account(email))
                    menu.addAction(activate_action)

        menu.addSeparator()

        # Delete account action
        delete_action = QAction("🗑️ Delete Account", self)
        delete_action.triggered.connect(lambda: self.delete_account_with_confirmation(email))
        menu.addAction(delete_action)

        # Display the context menu
        menu.exec_(self.table.mapToGlobal(position))

    def deactivate_account(self, email):
        """Deactivate the specified account"""
        try:
            if self.account_manager.clear_active_account():
                self.load_accounts(preserve_limits=True)
                self.show_status_message(f"{email} has been deactivated", 3000)
            else:
                self.show_status_message(_('account_activation_failed'), 3000)
        except Exception as e:
            self.show_status_message(f"{_('error')}: {str(e)}", 5000)

    def delete_account_with_confirmation(self, email):
        """Delete an account after confirmation"""
        try:
            reply = QMessageBox.question(self, "Delete Account",
                                       f"Are you sure you want to delete '{email}'?\n\n"
                                       "This action cannot be undone!",
                                       QMessageBox.Yes | QMessageBox.No,
                                       QMessageBox.No)

            if reply == QMessageBox.Yes:
                if self.account_manager.delete_account(email):
                    self.load_accounts(preserve_limits=True)
                    self.show_status_message(f"{email} has been deleted", 3000)
                else:
                    self.show_status_message("Account could not be deleted", 3000)
        except Exception as e:
            self.show_status_message(f"Deletion error: {str(e)}", 5000)

    def add_account(self):
        """Open the account addition dialog"""
        dialog = AddAccountDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            json_data = dialog.get_json_data()
            if json_data:
                success, message = self.account_manager.add_account(json_data)
                if success:
                    self.load_accounts()
                    self.status_bar.showMessage(_('account_added_success'), 3000)
                else:
                    self.status_bar.showMessage(f"{_('error')}: {message}", 5000)

    def refresh_limits(self):
        """Refresh stored limit information for all accounts"""
        accounts = self.account_manager.get_accounts_with_health()
        if not accounts:
            self.status_bar.showMessage(_('no_accounts_to_update'), 3000)
            return

        # Display progress dialog
        self.progress_dialog = QProgressDialog(_('updating_limits'), _('cancel'), 0, 100, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.show()

        # Launch background worker
        self.worker = TokenRefreshWorker(accounts, self.proxy_enabled)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.refresh_finished)
        self.worker.error.connect(self.refresh_error)
        self.worker.start()

        # Disable buttons while refresh is running
        self.refresh_limits_button.setEnabled(False)
        self.add_account_button.setEnabled(False)

    def update_progress(self, value, text):
        """Update progress dialog state"""
        self.progress_dialog.setValue(value)
        self.progress_dialog.setLabelText(text)

    def refresh_finished(self, results):
        """Handle completion of the refresh worker"""
        self.progress_dialog.close()

        # Reload table to display updated values
        self.load_accounts()

        # Re-enable buttons
        self.refresh_limits_button.setEnabled(True)
        self.add_account_button.setEnabled(True)

        self.status_bar.showMessage(_('accounts_updated', len(results)), 3000)

    def refresh_error(self, error_message):
        """Handle errors from the refresh worker"""
        self.progress_dialog.close()
        self.refresh_limits_button.setEnabled(True)
        self.add_account_button.setEnabled(True)
        self.status_bar.showMessage(f"{_('error')}: {error_message}", 5000)

    def start_proxy_and_activate_account(self, email):
        """Start the proxy and activate the selected account"""
        try:
            # Start mitmproxy
            print(f"Starting proxy and activating {email}...")

            # Show progress dialog while starting proxy
            progress = QProgressDialog(_('proxy_starting_account').format(email), _('cancel'), 0, 0, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            QApplication.processEvents()

            if self.proxy_manager.start(parent_window=self):
                progress.setLabelText(_('proxy_configuring'))
                QApplication.processEvents()

                proxy_url = self.proxy_manager.get_proxy_url()
                print(f"Proxy URL: {proxy_url}")

                ok = True
                if IS_WINDOWS and ProxyManager is not None:
                    ok = ProxyManager.set_proxy(proxy_url)
                else:
                    # On Linux inform user to configure browser/system proxy
                    self.status_bar.showMessage(f"Set your system/browser proxy to {proxy_url}", 5000)

                if ok:
                    progress.setLabelText(_('activating_account').format(email))
                    QApplication.processEvents()

                    self.proxy_enabled = True
                    self.proxy_start_button.setEnabled(False)
                    self.proxy_start_button.setText(_('proxy_active'))
                    self.proxy_stop_button.setVisible(True)
                    self.proxy_stop_button.setEnabled(True)

                    # Ensure refresh timer runs
                    if hasattr(self, 'active_account_refresh_timer') and not self.active_account_refresh_timer.isActive():
                        self.active_account_refresh_timer.start(60000)

                    # Activate the account now that proxy is ready
                    self.activate_account(email)

                    progress.close()

                    self.status_bar.showMessage(_('proxy_started_account_activated').format(email), 5000)
                    print(f"Proxy started successfully and {email} activated!")
                    return True
                else:
                    progress.close()
                    print("Windows proxy settings could not be configured")
                    self.proxy_manager.stop()
                    self.status_bar.showMessage(_('windows_proxy_config_failed'), 5000)
                    return False
            else:
                progress.close()
                print("Mitmproxy failed to start")
                self.status_bar.showMessage(_('mitmproxy_start_failed'), 5000)
                return False
        except Exception as e:
            if 'progress' in locals():
                progress.close()
            print(f"Proxy startup error: {e}")
            self.status_bar.showMessage(_('proxy_start_error').format(str(e)), 5000)
            return False

    def start_proxy(self):
        """Start only the proxy (legacy entry point)"""
        try:
            # Start mitmproxy
            print("Starting proxy...")

            # Show progress dialog during startup
            progress = QProgressDialog(_('proxy_starting'), _('cancel'), 0, 0, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            QApplication.processEvents()

            if self.proxy_manager.start(parent_window=self):
                progress.setLabelText(_('proxy_configuring'))
                QApplication.processEvents()

                proxy_url = self.proxy_manager.get_proxy_url()
                print(f"Proxy URL: {proxy_url}")

                ok = True
                if IS_WINDOWS and ProxyManager is not None:
                    ok = ProxyManager.set_proxy(proxy_url)
                else:
                    self.status_bar.showMessage(f"Set your system/browser proxy to {proxy_url}", 5000)

                if ok:
                    progress.close()

                    self.proxy_enabled = True
                    self.proxy_start_button.setEnabled(False)
                    self.proxy_start_button.setText(_('proxy_active'))
                    self.proxy_stop_button.setVisible(True)
                    self.proxy_stop_button.setEnabled(True)

                    # Ensure refresh timer runs
                    if hasattr(self, 'active_account_refresh_timer') and not self.active_account_refresh_timer.isActive():
                        self.active_account_refresh_timer.start(60000)

                    # Refresh table to reflect proxy state
                    self.load_accounts()

                    self.status_bar.showMessage(f"Proxy started at {proxy_url}", 5000)
                    print("Proxy started successfully!")
                else:
                    progress.close()
                    print("Windows proxy settings could not be configured")
                    self.proxy_manager.stop()
                    self.status_bar.showMessage(_('windows_proxy_config_failed'), 5000)
            else:
                progress.close()
                print("Mitmproxy failed to start")
                self.status_bar.showMessage(_('mitmproxy_start_failed'), 5000)
        except Exception as e:
            if 'progress' in locals():
                progress.close()
            print(f"Proxy startup error: {e}")
            self.status_bar.showMessage(_('proxy_start_error').format(str(e)), 5000)

    def stop_proxy(self):
        """Stop the proxy and clean up state"""
        try:
            # Disable Windows proxy settings
            if IS_WINDOWS and ProxyManager is not None:
                ProxyManager.disable_proxy()

            # Stop mitmproxy
            self.proxy_manager.stop()

            # Clear active account reference
            self.account_manager.clear_active_account()

            # Stop active account refresh timer
            if hasattr(self, 'active_account_refresh_timer') and self.active_account_refresh_timer.isActive():
                self.active_account_refresh_timer.stop()
                print("🔄 Active account refresh timer stopped")

            self.proxy_enabled = False
            self.proxy_start_button.setEnabled(True)
            self.proxy_start_button.setText(_('proxy_start'))
            self.proxy_stop_button.setVisible(False)
            self.proxy_stop_button.setEnabled(False)

            # Refresh displayed accounts
            self.load_accounts(preserve_limits=True)

            self.status_bar.showMessage(_('proxy_stopped'), 3000)
        except Exception as e:
            self.status_bar.showMessage(_('proxy_stop_error').format(str(e)), 5000)

    def activate_account(self, email):
        """Activate the selected account"""
        try:
            # Retrieve account state/details
            accounts_with_health = self.account_manager.get_accounts_with_health()
            account_data = None
            health_status = None

            for acc_email, acc_json, acc_health in accounts_with_health:
                if acc_email == email:
                    account_data = json.loads(acc_json)
                    health_status = acc_health
                    break

            if not account_data:
                self.status_bar.showMessage(_('account_not_found'), 3000)
                return

            # Prevent activation for banned accounts
            if health_status == 'banned':
                self.status_bar.showMessage(_('account_banned_cannot_activate').format(email), 5000)
                return

            # Check token expiration
            current_time = int(time.time() * 1000)
            expiration_time = account_data['stsTokenManager']['expirationTime']

            if current_time >= expiration_time:
                # Token expired; run refresh worker
                self.start_token_refresh(email, account_data)
                return

            # Token is valid, activate immediately
            self._complete_account_activation(email)

        except Exception as e:
            self.status_bar.showMessage(_('account_activation_error').format(str(e)), 5000)

    def start_token_refresh(self, email, account_data):
        """Start a background token refresh operation"""
        # If another token worker is running, do not start a new one
        if self.token_worker and self.token_worker.isRunning():
            self.status_bar.showMessage(_('token_refresh_in_progress'), 3000)
            return

        # Show progress dialog
        self.token_progress_dialog = QProgressDialog(_('token_refreshing').format(email), _('cancel'), 0, 0, self)
        self.token_progress_dialog.setWindowModality(Qt.WindowModal)
        self.token_progress_dialog.show()

        # Launch token worker thread
        self.token_worker = TokenWorker(email, account_data, self.proxy_enabled)
        self.token_worker.progress.connect(self.update_token_progress)
        self.token_worker.finished.connect(self.token_refresh_finished)
        self.token_worker.error.connect(self.token_refresh_error)
        self.token_worker.start()

    def update_token_progress(self, message):
        """Update progress text during token refresh"""
        if self.token_progress_dialog:
            self.token_progress_dialog.setLabelText(message)

    def token_refresh_finished(self, success, message):
        """Handle completion of token refresh"""
        if self.token_progress_dialog:
            self.token_progress_dialog.close()
            self.token_progress_dialog = None

        self.status_bar.showMessage(message, 3000)

        if success:
            # Token refreshed successfully; activate account
            email = self.token_worker.email
            self._complete_account_activation(email)

        # Clear worker reference
        self.token_worker = None

    def token_refresh_error(self, error_message):
        """Handle token refresh errors"""
        if self.token_progress_dialog:
            self.token_progress_dialog.close()
            self.token_progress_dialog = None

        self.status_bar.showMessage(_('token_refresh_error').format(error_message), 5000)
        self.token_worker = None

    def _complete_account_activation(self, email):
        """Finalize account activation flow"""
        try:
            if self.account_manager.set_active_account(email):
                self.load_accounts(preserve_limits=True)
                self.status_bar.showMessage(_('account_activated').format(email), 3000)
                self.notify_proxy_active_account_change()

                # Ensure user_settings.json exists (fetch if missing)
                self.check_and_fetch_user_settings(email)
            else:
                self.status_bar.showMessage(_('account_activation_failed'), 3000)
        except Exception as e:
            self.status_bar.showMessage(_('account_activation_error').format(str(e)), 5000)

    def check_and_fetch_user_settings(self, email):
        """Ensure user_settings.json exists; fetch via API when needed"""
        try:
            import os
            user_settings_path = "user_settings.json"

            # Create file if missing
            if not os.path.exists(user_settings_path):
                print(f"🔍 user_settings.json not found, calling API for {email}...")
                self.fetch_and_save_user_settings(email)
            else:
                print("✅ user_settings.json present, skipping API call")
        except Exception as e:
            print(f"user_settings check error: {e}")

    def fetch_and_save_user_settings(self, email):
        """Call GetUpdatedCloudObjects API and persist response to user_settings.json"""
        try:
            # Get dynamic OS information
            os_info = get_os_info()

            # Retrieve active account token
            accounts = self.account_manager.get_accounts()
            account_data = None

            for acc_email, acc_json in accounts:
                if acc_email == email:
                    account_data = json.loads(acc_json)
                    break

            if not account_data:
                print(f"❌ Account not found: {email}")
                return False

            access_token = account_data['stsTokenManager']['accessToken']

            # Prepare API request
            url = "https://app.warp.dev/graphql/v2?op=GetUpdatedCloudObjects"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}',
                'X-Warp-Client-Version': 'v0.2025.09.01.20.54.stable_04',
                'X-Warp-Os-Category': os_info['category'],
                'X-Warp-Os-Name': os_info['name'],
                'X-Warp-Os-Version': os_info['version'],
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }

            # GraphQL query ve variables
            payload = {
                "query": """query GetUpdatedCloudObjects($input: UpdatedCloudObjectsInput!, $requestContext: RequestContext!) {
  updatedCloudObjects(input: $input, requestContext: $requestContext) {
    __typename
    ... on UpdatedCloudObjectsOutput {
      actionHistories {
        actions {
          __typename
          ... on BundledActions {
            actionType
            count
            latestProcessedAtTimestamp
            latestTimestamp
            oldestTimestamp
          }
          ... on SingleAction {
            actionType
            processedAtTimestamp
            timestamp
          }
        }
        latestProcessedAtTimestamp
        latestTimestamp
        objectType
        uid
      }
      deletedObjectUids {
        folderUids
        genericStringObjectUids
        notebookUids
        workflowUids
      }
      folders {
        name
        metadata {
          creatorUid
          currentEditorUid
          isWelcomeObject
          lastEditorUid
          metadataLastUpdatedTs
          parent {
            __typename
            ... on FolderContainer {
              folderUid
            }
            ... on Space {
              uid
              type
            }
          }
          revisionTs
          trashedTs
          uid
        }
        permissions {
          guests {
            accessLevel
            source {
              __typename
              ... on FolderContainer {
                folderUid
              }
              ... on Space {
                uid
                type
              }
            }
            subject {
              __typename
              ... on UserGuest {
                firebaseUid
              }
              ... on PendingUserGuest {
                email
              }
            }
          }
          lastUpdatedTs
          anyoneLinkSharing {
            accessLevel
            source {
              __typename
              ... on FolderContainer {
                folderUid
              }
              ... on Space {
                uid
                type
              }
            }
          }
          space {
            uid
            type
          }
        }
        isWarpPack
      }
      genericStringObjects {
        format
        metadata {
          creatorUid
          currentEditorUid
          isWelcomeObject
          lastEditorUid
          metadataLastUpdatedTs
          parent {
            __typename
            ... on FolderContainer {
              folderUid
            }
            ... on Space {
              uid
              type
            }
          }
          revisionTs
          trashedTs
          uid
        }
        permissions {
          guests {
            accessLevel
            source {
              __typename
              ... on FolderContainer {
                folderUid
              }
              ... on Space {
                uid
                type
              }
            }
            subject {
              __typename
              ... on UserGuest {
                firebaseUid
              }
              ... on PendingUserGuest {
                email
              }
            }
          }
          lastUpdatedTs
          anyoneLinkSharing {
            accessLevel
            source {
              __typename
              ... on FolderContainer {
                folderUid
              }
              ... on Space {
                uid
                type
              }
            }
          }
          space {
            uid
            type
          }
        }
        serializedModel
      }
      notebooks {
        data
        title
        metadata {
          creatorUid
          currentEditorUid
          isWelcomeObject
          lastEditorUid
          metadataLastUpdatedTs
          parent {
            __typename
            ... on FolderContainer {
              folderUid
            }
            ... on Space {
              uid
              type
            }
          }
          revisionTs
          trashedTs
          uid
        }
        permissions {
          guests {
            accessLevel
            source {
              __typename
              ... on FolderContainer {
                folderUid
              }
              ... on Space {
                uid
                type
              }
            }
            subject {
              __typename
              ... on UserGuest {
                firebaseUid
              }
              ... on PendingUserGuest {
                email
              }
            }
          }
          lastUpdatedTs
          anyoneLinkSharing {
            accessLevel
            source {
              __typename
              ... on FolderContainer {
                folderUid
              }
              ... on Space {
                uid
                type
              }
            }
          }
          space {
            uid
            type
          }
        }
      }
      responseContext {
        serverVersion
      }
      userProfiles {
        displayName
        email
        photoUrl
        uid
      }
      workflows {
        data
        metadata {
          creatorUid
          currentEditorUid
          isWelcomeObject
          lastEditorUid
          metadataLastUpdatedTs
          parent {
            __typename
            ... on FolderContainer {
              folderUid
            }
            ... on Space {
              uid
              type
            }
          }
          revisionTs
          trashedTs
          uid
        }
        permissions {
          guests {
            accessLevel
            source {
              __typename
              ... on FolderContainer {
                folderUid
              }
              ... on Space {
                uid
                type
              }
            }
            subject {
              __typename
              ... on UserGuest {
                firebaseUid
              }
              ... on PendingUserGuest {
                email
              }
            }
          }
          lastUpdatedTs
          anyoneLinkSharing {
            accessLevel
            source {
              __typename
              ... on FolderContainer {
                folderUid
              }
              ... on Space {
                uid
                type
              }
            }
          }
          space {
            uid
            type
          }
        }
      }
    }
    ... on UserFacingError {
      error {
        __typename
        ... on SharedObjectsLimitExceeded {
          limit
          objectType
          message
        }
        ... on PersonalObjectsLimitExceeded {
          limit
          objectType
          message
        }
        ... on AccountDelinquencyError {
          message
        }
        ... on GenericStringObjectUniqueKeyConflict {
          message
        }
      }
      responseContext {
        serverVersion
      }
    }
  }
}""",
                "variables": {
                    "input": {
                        "folders": [
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.132139Z", "permissionsTs": "2025-09-04T15:14:09.132139Z", "revisionTs": "2025-09-04T15:14:09.132139Z", "uid": "EDD5BxHhckNftq2AqF16y0"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:51.073272Z", "permissionsTs": "2025-09-04T15:15:51.073272Z", "revisionTs": "2025-09-04T15:15:51.073272Z", "uid": "VtF6FwDkPcgMKjkEW0i011"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.397772Z", "permissionsTs": "2025-09-04T15:17:17.397772Z", "revisionTs": "2025-09-04T15:17:17.397772Z", "uid": "J13I26jNGbrV2OV8HUn7WJ"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:50.956728Z", "permissionsTs": "2025-09-04T15:15:50.956728Z", "revisionTs": "2025-09-04T15:15:50.956728Z", "uid": "8apsBUk0x5243ZYdCVu9lB"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.496422Z", "permissionsTs": "2025-09-04T15:17:17.496422Z", "revisionTs": "2025-09-04T15:17:17.496422Z", "uid": "m6ufDjY2pqQFk5Mz65BCNx"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.023623Z", "permissionsTs": "2025-09-04T15:14:09.023623Z", "revisionTs": "2025-09-04T15:14:09.023623Z", "uid": "kVsPIbczwIva4hLbHZMouT"}
                        ],
                        "forceRefresh": False,
                        "genericStringObjects": [
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:16:07.403093Z", "permissionsTs": None, "revisionTs": "2025-09-04T15:16:07.403093Z", "uid": "rYPkTIutkV8CjPI7T7oORM"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:53.983781Z", "permissionsTs": None, "revisionTs": "2025-09-04T15:17:53.983781Z", "uid": "P6to7VPbCHk0JwB3gqRGX6"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:03.045160Z", "permissionsTs": None, "revisionTs": "2025-09-04T15:15:03.045160Z", "uid": "pbwvZnbU8bJvmEIsKjXfBw"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:16:07.403093Z", "permissionsTs": None, "revisionTs": "2025-09-04T15:16:07.403093Z", "uid": "xrpRwHBwAI4nj21YHaVl7i"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:28.273803Z", "permissionsTs": "2025-09-04T15:14:28.273803Z", "revisionTs": "2025-09-04T15:14:28.273803Z", "uid": "5NqwjuMw606Zjk9d4bNbAo"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:02.982064Z", "permissionsTs": "2025-09-04T15:15:02.982064Z", "revisionTs": "2025-09-04T15:15:02.982064Z", "uid": "BCzdHbP76LQphANlQfUmVP"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:16:08.136555Z", "permissionsTs": None, "revisionTs": "2025-09-04T15:16:08.136555Z", "uid": "SGbrqUIVT2WfOUwLhj4yp0"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:27.597151Z", "permissionsTs": "2025-09-04T15:14:27.597151Z", "revisionTs": "2025-09-04T15:14:27.597151Z", "uid": "0IIBDzTfGNfA2GEkgF2QjN"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:28.273803Z", "permissionsTs": "2025-09-04T15:14:28.273803Z", "revisionTs": "2025-09-04T15:14:28.273803Z", "uid": "GcalSGa8Aprrcmvx5G2NLL"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:03.045160Z", "permissionsTs": None, "revisionTs": "2025-09-04T15:15:03.045160Z", "uid": "LDJfBBCEErAZSzg6hpCY4A"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:16:07.403093Z", "permissionsTs": None, "revisionTs": "2025-09-04T15:16:07.403093Z", "uid": "AHrIt6mfJi7NdsIBiSA0tz"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:27.597151Z", "permissionsTs": "2025-09-04T15:14:27.597151Z", "revisionTs": "2025-09-04T15:14:27.597151Z", "uid": "fkI3MiLCjKhHrGf9n6O0Yo"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:53.983781Z", "permissionsTs": None, "revisionTs": "2025-09-04T15:17:53.983781Z", "uid": "DZKY9uei132xJ5Mq5MBw6T"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:53.983781Z", "permissionsTs": None, "revisionTs": "2025-09-04T15:17:53.983781Z", "uid": "CkjKbSV08kRoYGUEY9LvfY"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:54.625539Z", "permissionsTs": None, "revisionTs": "2025-09-04T15:17:54.625539Z", "uid": "7oQYxEq7ZpEXDcE9t4EAYC"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:16:08.136555Z", "permissionsTs": None, "revisionTs": "2025-09-04T15:16:08.136555Z", "uid": "am8aJIQHuondndQFyfHa4i"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:27.597151Z", "permissionsTs": "2025-09-04T15:14:27.597151Z", "revisionTs": "2025-09-04T15:14:27.597151Z", "uid": "HGht23AnvjqHuT8UwCYNAO"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:54.625539Z", "permissionsTs": None, "revisionTs": "2025-09-04T15:17:54.625539Z", "uid": "V8mjwCcOVAvHOFXfy93rwI"}
                        ],
                        "notebooks": [
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:51.211785Z", "permissionsTs": "2025-09-04T15:15:51.211785Z", "revisionTs": "2025-09-04T15:15:51.211785Z", "uid": "UdtjGuGcUYIGpZjZlgC764"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.253619Z", "permissionsTs": "2025-09-04T15:14:09.253619Z", "revisionTs": "2025-09-04T15:14:09.253619Z", "uid": "bDbGHWpn4uca3EFGTH1U2Q"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.603173Z", "permissionsTs": "2025-09-04T15:17:17.603173Z", "revisionTs": "2025-09-04T15:17:17.603173Z", "uid": "jauSUuyNTBgbBuWiE8TUHY"}
                        ],
                        "workflows": [
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.552627Z", "permissionsTs": "2025-09-04T15:17:17.552627Z", "revisionTs": "2025-09-04T15:17:17.552627Z", "uid": "iwMafgTRhaYK0Iw3cse39R"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.552627Z", "permissionsTs": "2025-09-04T15:17:17.552627Z", "revisionTs": "2025-09-04T15:17:17.552627Z", "uid": "NWGQamxykgd5ypAdqqFKsM"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.192955Z", "permissionsTs": "2025-09-04T15:14:09.192955Z", "revisionTs": "2025-09-04T15:14:09.192955Z", "uid": "RqUpAjdKD6kRvIyVaDo1uB"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.552627Z", "permissionsTs": "2025-09-04T15:17:17.552627Z", "revisionTs": "2025-09-04T15:17:17.552627Z", "uid": "VVnHPmOGnL158geO9QjMzH"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.192955Z", "permissionsTs": "2025-09-04T15:14:09.192955Z", "revisionTs": "2025-09-04T15:14:09.192955Z", "uid": "D2H43FGrjjUj87Xtz4faGH"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.552627Z", "permissionsTs": "2025-09-04T15:17:17.552627Z", "revisionTs": "2025-09-04T15:17:17.552627Z", "uid": "MFyXwtpP1Yw6pcinj03n2n"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.552627Z", "permissionsTs": "2025-09-04T15:17:17.552627Z", "revisionTs": "2025-09-04T15:17:17.552627Z", "uid": "VXuPYgyHagWEFmRs3Nw7bs"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.192955Z", "permissionsTs": "2025-09-04T15:14:09.192955Z", "revisionTs": "2025-09-04T15:14:09.192955Z", "uid": "CfO2BNrKtpxosE7BarOhzF"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:51.140134Z", "permissionsTs": "2025-09-04T15:15:51.140134Z", "revisionTs": "2025-09-04T15:15:51.140134Z", "uid": "2qvtn32aHqe1h0tgjTXJLH"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.192955Z", "permissionsTs": "2025-09-04T15:14:09.192955Z", "revisionTs": "2025-09-04T15:14:09.192955Z", "uid": "JIzhs7KX6R7q1469U0OkAx"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.192955Z", "permissionsTs": "2025-09-04T15:14:09.192955Z", "revisionTs": "2025-09-04T15:14:09.192955Z", "uid": "EgE7149EOK5HZlg33UG55A"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:51.019199Z", "permissionsTs": "2025-09-04T15:15:51.019199Z", "revisionTs": "2025-09-04T15:15:51.019199Z", "uid": "v7gvOPIm5MDbfTiZfY1PrZ"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:51.140134Z", "permissionsTs": "2025-09-04T15:15:51.140134Z", "revisionTs": "2025-09-04T15:15:51.140134Z", "uid": "ZgbNP7xZFDMI2mlfufMpoH"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.454688Z", "permissionsTs": "2025-09-04T15:17:17.454688Z", "revisionTs": "2025-09-04T15:17:17.454688Z", "uid": "GKk36aCOvwgUnas8YGrm5t"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:51.140134Z", "permissionsTs": "2025-09-04T15:15:51.140134Z", "revisionTs": "2025-09-04T15:15:51.140134Z", "uid": "HZeCcSc8pdwBJCLVtBfcyO"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.552627Z", "permissionsTs": "2025-09-04T15:17:17.552627Z", "revisionTs": "2025-09-04T15:17:17.552627Z", "uid": "wkIO1y9MBx6qBtJm8hSX5H"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:51.019199Z", "permissionsTs": "2025-09-04T15:15:51.019199Z", "revisionTs": "2025-09-04T15:15:51.019199Z", "uid": "vQwM7UBNFCm08dYwvs1yBA"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.552627Z", "permissionsTs": "2025-09-04T15:17:17.552627Z", "revisionTs": "2025-09-04T15:17:17.552627Z", "uid": "EWkCGy5fVCn6LzKZ3aap7n"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:51.019199Z", "permissionsTs": "2025-09-04T15:15:51.019199Z", "revisionTs": "2025-09-04T15:15:51.019199Z", "uid": "1cYEBtjukUIbF4vhTGEL3C"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:51.140134Z", "permissionsTs": "2025-09-04T15:15:51.140134Z", "revisionTs": "2025-09-04T15:15:51.140134Z", "uid": "Hp7Rd4X9Cz1E1EuvwLSDRf"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.192955Z", "permissionsTs": "2025-09-04T15:14:09.192955Z", "revisionTs": "2025-09-04T15:14:09.192955Z", "uid": "gnT8FcrxNhqFBzuGr3Rpmr"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.083649Z", "permissionsTs": "2025-09-04T15:14:09.083649Z", "revisionTs": "2025-09-04T15:14:09.083649Z", "uid": "kDomyveR7d4nLXSmGGh5sm"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:51.140134Z", "permissionsTs": "2025-09-04T15:15:51.140134Z", "revisionTs": "2025-09-04T15:15:51.140134Z", "uid": "UpAfUQYo4UfUj0hay0REri"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.454688Z", "permissionsTs": "2025-09-04T15:17:17.454688Z", "revisionTs": "2025-09-04T15:17:17.454688Z", "uid": "PRy3g6EKx6HlA0CF4tBfFd"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:51.140134Z", "permissionsTs": "2025-09-04T15:15:51.140134Z", "revisionTs": "2025-09-04T15:15:51.140134Z", "uid": "Fm9NQzwF6U3lLIWMWAvtEY"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:17:17.454688Z", "permissionsTs": "2025-09-04T15:17:17.454688Z", "revisionTs": "2025-09-04T15:17:17.454688Z", "uid": "dWtnvCRrHazYVFBb9QMo1B"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.083649Z", "permissionsTs": "2025-09-04T15:14:09.083649Z", "revisionTs": "2025-09-04T15:14:09.083649Z", "uid": "mCl51EOXLpiExaHl1knxUB"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.192955Z", "permissionsTs": "2025-09-04T15:14:09.192955Z", "revisionTs": "2025-09-04T15:14:09.192955Z", "uid": "PVZgftdFpFR4BN2k9AmCBw"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:15:51.140134Z", "permissionsTs": "2025-09-04T15:15:51.140134Z", "revisionTs": "2025-09-04T15:15:51.140134Z", "uid": "wKSGpwXdQJgs4Bbl5ZGeEc"},
                            {"actionsTs": None, "metadataTs": "2025-09-04T15:14:09.083649Z", "permissionsTs": "2025-09-04T15:14:09.083649Z", "revisionTs": "2025-09-04T15:14:09.083649Z", "uid": "mJg9qgqMkWSYytyq8Z7yym"}
                        ]
                    },
                    "requestContext": {
                        "clientContext": {"version": "v0.2025.09.01.20.54.stable_04"},
                        "osContext": {"category": os_info['category'], "linuxKernelVersion": None, "name": os_info['category'], "version": "10 (19045)"}
                    }
                },
                "operationName": "GetUpdatedCloudObjects"
            }

            # Invoke the API directly without proxying
            proxies = {'http': None, 'https': None}
            response = requests.post(url, headers=headers, json=payload, timeout=60, verify=False, proxies=proxies)

            if response.status_code == 200:
                user_settings_data = response.json()

                # Persist response to user_settings.json
                with open("user_settings.json", 'w', encoding='utf-8') as f:
                    json.dump(user_settings_data, f, indent=2, ensure_ascii=False)

                print(f"✅ user_settings.json created successfully ({email})")
                self.status_bar.showMessage(f"🔄 Downloaded user settings for {email}", 3000)
                return True
            else:
                print(f"❌ API request failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"user_settings fetch error: {e}")
            return False

    def notify_proxy_active_account_change(self):
        """Inform the proxy script about the new active account"""
        try:
            # Check whether the proxy is running
            if hasattr(self, 'proxy_manager') and self.proxy_manager.is_running():
                print("📢 Notifying proxy about active account change...")

                # File-based trigger mechanism for reliability
                import time
                trigger_file = "account_change_trigger.tmp"
                try:
                    with open(trigger_file, 'w') as f:
                        f.write(str(int(time.time())))
                    print("✅ Proxy trigger file created")
                except Exception as e:
                    print(f"Trigger file creation error: {e}")

                print("✅ Proxy notified about account change")
            else:
                print("ℹ️  Proxy is not running, account change notification skipped")
        except Exception as e:
            print(f"Proxy notification error: {e}")

    def refresh_account_token(self, email, account_data):
        """Refresh the token for a specific account"""
        try:
            refresh_token = account_data['stsTokenManager']['refreshToken']
            api_key = account_data['apiKey']

            url = f"https://securetoken.googleapis.com/v1/token?key={api_key}"
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'WarpAccountManager/1.0'  # Tag request with manager-specific user agent
            }
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token
            }

            # Establish direct connection without proxy
            proxies = {'http': None, 'https': None} if self.proxy_enabled else None
            response = requests.post(url, json=data, headers=headers, timeout=30,
                                   verify=not self.proxy_enabled, proxies=proxies)

            if response.status_code == 200:
                token_data = response.json()
                new_token_data = {
                    'accessToken': token_data['access_token'],
                    'refreshToken': token_data['refresh_token'],
                    'expirationTime': int(time.time() * 1000) + (int(token_data['expires_in']) * 1000)
                }

                return self.account_manager.update_account_token(email, new_token_data)
            return False
        except Exception as e:
            print(f"Token refresh error: {e}")
            return False

    def check_proxy_status(self):
        """Monitor proxy status and handle unexpected stops"""
        if self.proxy_enabled:
            if not self.proxy_manager.is_running():
                # Proxy stopped unexpectedly
                self.proxy_enabled = False
                self.proxy_start_button.setEnabled(True)
                self.proxy_start_button.setText(_('proxy_start'))
                self.proxy_stop_button.setVisible(False)
                self.proxy_stop_button.setEnabled(False)
                ProxyManager.disable_proxy()
                self.account_manager.clear_active_account()
                self.load_accounts(preserve_limits=True)

                self.status_bar.showMessage(_('proxy_unexpected_stop'), 5000)

    def check_ban_notifications(self):
        """Check for ban notifications emitted by proxy script"""
        try:
            import os

            ban_notification_file = "ban_notification.tmp"
            if os.path.exists(ban_notification_file):
                # Read notification details
                with open(ban_notification_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()

                if content:
                    # Extract email and timestamp
                    parts = content.split('|')
                    if len(parts) >= 2:
                        banned_email = parts[0]
                        timestamp = parts[1]

                        print(f"Ban notification received: {banned_email} (timestamp: {timestamp})")

                        # Refresh account list
                        self.load_accounts(preserve_limits=True)

                        # Inform user about ban status
                        self.show_status_message(f"⛔ {banned_email} account has been banned!", 8000)

                # Remove temporary notification file
                os.remove(ban_notification_file)
                print("Ban notification file removed")

        except Exception as e:
            # Ignore missing file or read errors
            pass

    def refresh_active_account(self):
        """Refresh active account token and limit every 60 seconds"""
        try:
            # Stop timer if proxy is no longer active
            if not self.proxy_enabled:
                if self.active_account_refresh_timer.isActive():
                    self.active_account_refresh_timer.stop()
                    print("🔄 Active account refresh timer stopped (proxy disabled)")
                return

            # Retrieve active account email
            active_email = self.account_manager.get_active_account()
            if not active_email:
                return

            print(f"🔄 Refreshing active account: {active_email}")

            # Fetch account data from database
            accounts_with_health = self.account_manager.get_accounts_with_health_and_limits()
            active_account_data = None
            health_status = None

            for email, account_json, acc_health, limit_info in accounts_with_health:
                if email == active_email:
                    active_account_data = json.loads(account_json)
                    health_status = acc_health
                    break

            if not active_account_data:
                print(f"❌ Active account not found: {active_email}")
                return

            # Skip accounts that are banned
            if health_status == 'banned':
                print(f"⛔ Active account banned, skipping: {active_email}")
                return

            # Refresh token and limits
            self._refresh_single_active_account(active_email, active_account_data)

        except Exception as e:
            print(f"Active account refresh error: {e}")

    def _refresh_single_active_account(self, email, account_data):
        """Refresh token and limits for the given active account"""
        try:
            # Renew token
            if self.renew_single_token(email, account_data):
                print(f"✅ Active account token renewed: {email}")

                # Update limit metadata
                self._update_active_account_limit(email)

                # Reload table to reflect limit changes
                self.load_accounts(preserve_limits=False)
            else:
                print(f"❌ Active account token could not be renewed: {email}")
                self.account_manager.update_account_health(email, 'unhealthy')

        except Exception as e:
            print(f"Active account refresh error ({email}): {e}")

    def _update_active_account_limit(self, email):
        """Update cached limit information for the active account"""
        try:
            # Retrieve account data again
            accounts = self.account_manager.get_accounts()
            for acc_email, acc_json in accounts:
                if acc_email == email:
                    account_data = json.loads(acc_json)

                    # Fetch latest limit info
                    limit_info = self._get_account_limit_info(account_data)
                    if limit_info:
                        used = limit_info.get('requestsUsedSinceLastRefresh', 0)
                        total = limit_info.get('requestLimit', 0)
                        limit_text = f"{used}/{total}"

                        self.account_manager.update_account_limit_info(email, limit_text)
                        print(f"✅ Active account limit updated: {email} - {limit_text}")
                    else:
                        self.account_manager.update_account_limit_info(email, "N/A")
                        print(f"⚠️ Active account limit information unavailable: {email}")
                    break

        except Exception as e:
            print(f"Active account limit update error ({email}): {e}")

    def _get_account_limit_info(self, account_data):
        """Request limit information for an account from Warp API"""
        try:
            # Get dynamic OS information
            os_info = get_os_info()

            access_token = account_data['stsTokenManager']['accessToken']

            url = "https://app.warp.dev/graphql/v2?op=GetRequestLimitInfo"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}',
                'X-Warp-Client-Version': 'v0.2025.08.27.08.11.stable_04',
                'X-Warp-Os-Category': os_info['category'],
                'X-Warp-Os-Name': os_info['name'],
                'X-Warp-Os-Version': os_info['version'],
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'X-Warp-Manager-Request': 'true'
            }

            query = """
            query GetRequestLimitInfo($requestContext: RequestContext!) {
              user(requestContext: $requestContext) {
                __typename
                ... on UserOutput {
                  user {
                    requestLimitInfo {
                      isUnlimited
                      nextRefreshTime
                      requestLimit
                      requestsUsedSinceLastRefresh
                      requestLimitRefreshDuration
                      isUnlimitedAutosuggestions
                      acceptedAutosuggestionsLimit
                      acceptedAutosuggestionsSinceLastRefresh
                      isUnlimitedVoice
                      voiceRequestLimit
                      voiceRequestsUsedSinceLastRefresh
                      voiceTokenLimit
                      voiceTokensUsedSinceLastRefresh
                      isUnlimitedCodebaseIndices
                      maxCodebaseIndices
                      maxFilesPerRepo
                      embeddingGenerationBatchSize
                    }
                  }
                }
                ... on UserFacingError {
                  error {
                    __typename
                    ... on SharedObjectsLimitExceeded {
                      limit
                      objectType
                      message
                    }
                    ... on PersonalObjectsLimitExceeded {
                      limit
                      objectType
                      message
                    }
                    ... on AccountDelinquencyError {
                      message
                    }
                    ... on GenericStringObjectUniqueKeyConflict {
                      message
                    }
                  }
                  responseContext {
                    serverVersion
                  }
                }
              }
            }
            """

            payload = {
                "query": query,
                "variables": {
                    "requestContext": {
                        "clientContext": {
                            "version": "v0.2025.08.27.08.11.stable_04"
                        },
                        "osContext": {
                            "category": os_info['category'],
                            "linuxKernelVersion": None,
                            "name": os_info['category'],
                            "version": os_info['version']
                        }
                    }
                },
                "operationName": "GetRequestLimitInfo"
            }

            # Connect without using the proxy
            proxies = {'http': None, 'https': None}
            response = requests.post(url, headers=headers, json=payload, timeout=30,
                                   verify=True, proxies=proxies)

            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'user' in data['data']:
                    user_data = data['data']['user']
                    if user_data.get('__typename') == 'UserOutput':
                        return user_data['user']['requestLimitInfo']
            return None
        except Exception as e:
            print(f"Limit information retrieval error: {e}")
            return None

    def auto_renew_tokens(self):
        """Automatically refresh tokens every minute"""
        try:
            print("🔄 Starting automatic token check...")

            # Fetch all accounts with status info
            accounts = self.account_manager.get_accounts_with_health_and_limits()

            if not accounts:
                return

            expired_count = 0
            renewed_count = 0

            for email, account_json, health_status, limit_info in accounts:
                # Skip banned accounts
                if health_status == 'banned':
                    continue

                try:
                    account_data = json.loads(account_json)
                    expiration_time = account_data['stsTokenManager']['expirationTime']
                    current_time = int(time.time() * 1000)

                    # Renew tokens one minute before expiration
                    buffer_time = 1 * 60 * 1000
                    if current_time >= (expiration_time - buffer_time):
                        expired_count += 1
                        print(f"⏰ Token expiring soon: {email}")

                        # Attempt token refresh
                        if self.renew_single_token(email, account_data):
                            renewed_count += 1
                            print(f"✅ Token yenilendi: {email}")
                        else:
                            print(f"❌ Token yenilenemedi: {email}")

                except Exception as e:
                    print(f"Token check error ({email}): {e}")
                    continue

            # Present summary message
            if expired_count > 0:
                if renewed_count > 0:
                    self.show_status_message(f"🔄 Refreshed {renewed_count}/{expired_count} expiring tokens", 5000)
                    # Reload accounts to reflect changes
                    self.load_accounts(preserve_limits=True)
                else:
                    self.show_status_message(f"⚠️ Failed to refresh {expired_count} expiring tokens", 5000)
            else:
                print("✅ All tokens are valid")

        except Exception as e:
            print(f"Automatic token renewal error: {e}")
            self.show_status_message("❌ Token check failed", 3000)

    def renew_single_token(self, email, account_data):
        """Refresh the token for a single account"""
        try:
            refresh_token = account_data['stsTokenManager']['refreshToken']
            api_key = account_data.get('apiKey')

            if not api_key:
                raise ValueError("Firebase API key was not found")

            # Firebase token refresh endpoint
            url = f"https://securetoken.googleapis.com/v1/token?key={api_key}"

            payload = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            }

            headers = {
                "Content-Type": "application/json"
            }

            # Bypass proxy to call Firebase directly
            proxies = {'http': None, 'https': None}

            response = requests.post(url, json=payload, headers=headers,
                                   timeout=30, verify=True, proxies=proxies)

            if response.status_code == 200:
                token_data = response.json()

                # Update token details
                new_access_token = token_data['access_token']
                new_refresh_token = token_data.get('refresh_token', refresh_token)
                expires_in = int(token_data['expires_in']) * 1000

                # Compute new expiration time
                new_expiration_time = int(time.time() * 1000) + expires_in

                # Update in-memory account data
                account_data['stsTokenManager']['accessToken'] = new_access_token
                account_data['stsTokenManager']['refreshToken'] = new_refresh_token
                account_data['stsTokenManager']['expirationTime'] = new_expiration_time

                # Persist changes to database
                updated_json = json.dumps(account_data)
                self.account_manager.update_account(email, updated_json)

                return True
            else:
                print(f"Token refresh error: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"Token refresh error ({email}): {e}")
            return False

    def reset_status_message(self):
        """Restore the default status bar message"""
        debug_mode = os.path.exists("debug.txt")
        if debug_mode:
            default_message = _('default_status_debug')
        else:
            default_message = _('default_status')

        self.status_bar.showMessage(default_message)

    def show_status_message(self, message, timeout=5000):
        """Display a status message and schedule automatic reset"""
        self.status_bar.showMessage(message)

        # Start/reset the timer
        if timeout > 0:
            self.status_reset_timer.start(timeout)

    def show_help_dialog(self):
        """Display the help and usage guide dialog"""
        dialog = HelpDialog(self)
        dialog.exec_()

    def change_language(self, language_text):
        """Switch application language and refresh UI"""
        language_code = 'id' if language_text == 'ID' else 'en'
        get_language_manager().set_language(language_code)
        self.refresh_ui_texts()

    def refresh_ui_texts(self):
        """Refresh UI text labels according to selected language"""
        # Update window title
        self.setWindowTitle(_('app_title'))

        # Update button labels
        self.proxy_start_button.setText(_('proxy_start') if not self.proxy_enabled else _('proxy_active'))
        self.proxy_stop_button.setText(_('proxy_stop'))
        self.add_account_button.setText(_('add_account'))
        self.refresh_limits_button.setText(_('refresh_limits'))
        self.help_button.setText(_('help'))

        # Update table headers
        self.table.setHorizontalHeaderLabels([_('current'), _('email'), _('status'), _('limit')])

        # Reset status bar message to default
        debug_mode = os.path.exists("debug.txt")
        if debug_mode:
            self.status_bar.showMessage(_('default_status_debug'))
        else:
            self.status_bar.showMessage(_('default_status'))

        # Reload table to apply language changes
        self.load_accounts(preserve_limits=True)

    def on_account_added_via_bridge(self, email):
        """Refresh table when an account arrives via bridge"""
        try:
            print(f"🔄 Bridge: Tablo yenileniyor - {email}")
            # Emit signal from worker thread safely
            self.bridge_account_added.emit(email)
            print("✅ Bridge: Table refresh signal sent")
        except Exception as e:
            print(f"❌ Bridge: Table refresh error - {e}")

    def refresh_table_after_bridge_add(self, email):
        """Refresh table after bridge addition (runs on main thread)"""
        try:
            print(f"🔄 Ana thread'de tablo yenileniyor... ({email})")
            self.load_accounts(preserve_limits=True)

            # Notify user via status bar
            if email:
                self.status_bar.showMessage(f"✅ New account added via bridge: {email}", 5000)
            else:
                self.status_bar.showMessage("✅ New account added via bridge", 5000)
            print("✅ Table refreshed successfully")
        except Exception as e:
            print(f"❌ Main thread table refresh error: {e}")

    def closeEvent(self, event):
        """Perform cleanup when the application closes"""
        if self.proxy_enabled:
            self.stop_proxy()

        # Stop bridge server if running
        if hasattr(self, 'bridge_server'):
            self.bridge_server.stop()

        event.accept()


def main():
    app = QApplication(sys.argv)
    # Apply modern, compact visual style
    load_stylesheet(app)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
