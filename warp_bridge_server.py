#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HTTP server for Warp Account Bridge - Chrome extension integration
"""

import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
try:
    # Python 3.7+
    from http.server import ThreadingHTTPServer as _ThreadingHTTPServer
except ImportError:  # pragma: no cover
    from socketserver import ThreadingMixIn

    class _ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True
from urllib.parse import urlparse, parse_qs
import sqlite3
from languages import get_language_manager, _

class BridgeRequestHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, account_manager=None, on_account_added=None, **kwargs):
        self.account_manager = account_manager
        self.on_account_added = on_account_added
        super().__init__(*args, **kwargs)

    def _set_cors_headers(self):
        """CORS headers for browser requests"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Extension-ID')

    def _send_json_response(self, status_code, data):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self._set_cors_headers()
        self.end_headers()
        response_data = json.dumps(data, ensure_ascii=False)
        self.wfile.write(response_data.encode('utf-8'))

    def _verify_extension(self):
        """Verify request comes from our extension"""
        extension_id = self.headers.get('X-Extension-ID')
        return extension_id == 'warp-account-bridge-v1'

    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        """Handle GET requests"""
        parsed_url = urlparse(self.path)

        if parsed_url.path == '/health':
            # Health check endpoint
            self._send_json_response(200, {
                'status': 'ok',
                'service': 'warp-bridge',
                'timestamp': int(time.time())
            })
        else:
            self._send_json_response(404, {'error': 'Endpoint not found'})

    def do_POST(self):
        """Handle POST requests"""
        parsed_url = urlparse(self.path)

        if not self._verify_extension():
            self._send_json_response(403, {'error': 'Unauthorized - Invalid extension ID'})
            return

        if parsed_url.path == '/add-account':
            self._handle_add_account()
        elif parsed_url.path == '/setup-bridge':
            self._handle_setup_bridge()
        else:
            self._send_json_response(404, {'error': 'Endpoint not found'})

    def _handle_add_account(self):
        """Handle account addition from extension"""
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_json_response(400, {'error': 'Empty request body'})
                return

            body = self.rfile.read(content_length)
            account_data = json.loads(body.decode('utf-8'))

            # Validate account data structure
            if not self._validate_account_data(account_data):
                self._send_json_response(400, {'error': 'Invalid account data structure'})
                return

            # Convert to JSON string for AccountManager
            account_json = json.dumps(account_data, ensure_ascii=False)

            # Add account using AccountManager
            if self.account_manager:
                success, message = self.account_manager.add_account(account_json)

                if success:
                    print(f"✅ Bridge: Hesap eklendi - {account_data.get('email', 'Unknown')}")

                    # Yanıtı hemen döndür, UI yenilemeyi arka planda tetikle
                    self._send_json_response(200, {
                        'success': True,
                        'message': message,
                        'email': account_data.get('email')
                    })

                    if self.on_account_added:
                        try:
                            threading.Thread(
                                target=self.on_account_added,
                                args=(account_data.get('email'),),
                                daemon=True
                            ).start()
                        except Exception as e:
                            print(f"⚠️  Tablo güncelleme hatası: {e}")
                    return
                else:
                    print(f"❌ Bridge: Hesap ekleme hatası - {message}")
                    self._send_json_response(400, {
                        'success': False,
                        'error': message
                    })
            else:
                self._send_json_response(500, {'error': 'Account manager not available'})

        except json.JSONDecodeError:
            self._send_json_response(400, {'error': 'Invalid JSON data'})
        except Exception as e:
            print(f"❌ Bridge: Add account error - {str(e)}")
            self._send_json_response(500, {'error': f'Server error: {str(e)}'})

    def _handle_setup_bridge(self):
        """Handle bridge setup from extension"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = self.rfile.read(content_length)
                setup_data = json.loads(body.decode('utf-8'))
                print(f"🔗 Bridge: Extension connected - ID: {setup_data.get('extensionId', 'Unknown')}")

            self._send_json_response(200, {
                'success': True,
                'message': 'Bridge setup successful',
                'server_version': '1.0'
            })

        except Exception as e:
            print(f"❌ Bridge: Setup error - {str(e)}")
            self._send_json_response(500, {'error': f'Setup error: {str(e)}'})

    def _validate_account_data(self, data):
        """Validate account data structure"""
        try:
            # Check required fields
            required_fields = ['email', 'stsTokenManager']
            for field in required_fields:
                if field not in data:
                    return False

            # Check stsTokenManager structure
            sts_manager = data['stsTokenManager']
            required_sts_fields = ['accessToken', 'refreshToken']
            for field in required_sts_fields:
                if field not in sts_manager:
                    return False

            return True

        except Exception:
            return False

    def log_message(self, format, *args):
        """Override to reduce log noise"""
        pass  # Silent logging


class WarpBridgeServer:
    def __init__(self, account_manager, port=8765, on_account_added=None):
        self.account_manager = account_manager
        self.port = port
        self.server = None
        self.server_thread = None
        self.running = False
        self.on_account_added = on_account_added

    def start(self):
        """Start the bridge server"""
        try:
            # Create request handler with account_manager
            def handler(*args, **kwargs):
                return BridgeRequestHandler(*args, account_manager=self.account_manager,
                                          on_account_added=self.on_account_added, **kwargs)

            self.server = _ThreadingHTTPServer(('localhost', self.port), handler)
            try:
                self.server.daemon_threads = True
                self.server.allow_reuse_address = True
            except Exception:
                pass
            self.running = True

            # Start server in separate thread
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()

            print(f"🌉 Bridge Server başlatıldı: http://localhost:{self.port}")
            return True

        except Exception as e:
            print(f"❌ Bridge Server başlatma hatası: {e}")
            return False

    def _run_server(self):
        """Run the server in thread"""
        try:
            self.server.serve_forever()
        except Exception as e:
            if self.running:  # Only show error if we're supposed to be running
                print(f"❌ Bridge Server çalışma hatası: {e}")

    def stop(self):
        """Stop the bridge server"""
        if self.server and self.running:
            self.running = False
            self.server.shutdown()
            if self.server_thread:
                self.server_thread.join(timeout=2)
            print("🛑 Bridge Server durduruldu")

    def is_running(self):
        """Check if server is running"""
        return self.running and self.server_thread and self.server_thread.is_alive()


# Test function
if __name__ == "__main__":
    from warp_account_manager import AccountManager

    print("Testing Warp Bridge Server...")

    # Create account manager
    account_manager = AccountManager()

    # Start bridge server
    bridge = WarpBridgeServer(account_manager)

    if bridge.start():
        print("Bridge server is running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            bridge.stop()
            print("Bridge server stopped.")
    else:
        print("Failed to start bridge server.")
