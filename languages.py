#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import locale
import os


class LanguageManager:
    """Multilingual support manager."""

    def __init__(self):
        self.current_language = self.detect_system_language()
        self.translations = self.load_translations()

    def detect_system_language(self):
        """Detect the system language automatically."""
        try:
            try:
                system_locale = locale.getlocale()[0]
            except Exception:
                import warnings

                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    system_locale = locale.getdefaultlocale()[0]

            if system_locale:
                locale_lower = system_locale.lower()
                if (
                    locale_lower.startswith(("id", "in"))
                    or "indonesian" in locale_lower
                    or "bahasa" in locale_lower
                ):
                    return "id"

            return "en"
        except Exception:
            return "en"

    def load_translations(self):
        """Load translation dictionaries."""
        translations = {
            "id": {
                # General
                "app_title": "Pengelola Akun Warp",
                "yes": "Ya",
                "no": "Tidak",
                "ok": "OK",
                "cancel": "Batal",
                "close": "Tutup",
                "error": "Kesalahan",
                "success": "Berhasil",
                "warning": "Peringatan",
                "info": "Info",

                # Buttons
                "proxy_start": "Mulai Proxy",
                "proxy_stop": "Hentikan Proxy",
                "proxy_active": "Proxy Aktif",
                "add_account": "Tambah Akun",
                "refresh_limits": "Segarkan Batas",
                "help": "Bantuan",
                "activate": "🟢 Aktifkan",
                "deactivate": "🔴 Nonaktifkan",
                "delete_account": "🗑️ Hapus Akun",
                "create_account": "🌐 Buat Akun",
                "add": "Tambahkan",
                "copy_javascript": "📋 Salin Kode JavaScript",
                "copied": "✅ Disalin!",
                "copy_error": "❌ Kesalahan!",
                "open_certificate": "📁 Buka Berkas Sertifikat",
                "installation_complete": "✅ Instalasi Selesai",

                # Table headers
                "current": "Saat Ini",
                "email": "Email",
                "status": "Status",
                "limit": "Batas",

                # Activation button texts
                "button_active": "AKTIF",
                "button_inactive": "NONAKTIF",
                "button_banned": "BAN",
                "button_start": "Mulai",
                "button_stop": "Berhenti",

                # Status messages
                "status_active": "Aktif",
                "status_banned": "BAN",
                "status_token_expired": "Token Kedaluwarsa",
                "status_proxy_active": " (Proxy Aktif)",
                "status_error": "Kesalahan",
                "status_na": "N/A",
                "status_not_updated": "Belum Diperbarui",
                "status_healthy": "sehat",
                "status_unhealthy": "tidak sehat",
                "status_banned_key": "banned",

                # Add account
                "add_account_title": "Tambah Akun",
                "add_account_instruction": "Tempel data JSON akun di bawah:",
                "add_account_placeholder": "Tempel data JSON di sini...",
                "how_to_get_json": "❓ Cara mendapatkan data JSON?",
                "how_to_get_json_close": "❌ Tutup",
                "json_info_title": "Cara Mendapatkan Data JSON?",

                # Add account dialog tabs
                "tab_manual": "Manual",
                "tab_auto": "Otomatis",
                "manual_method_title": "Penambahan JSON Manual",
                "auto_method_title": "Penambahan Otomatis dengan Ekstensi Chrome",

                # Chrome extension description
                "chrome_extension_title": "🌐 Ekstensi Chrome",
                "chrome_extension_description": "Anda dapat menambahkan akun secara otomatis menggunakan ekstensi Chrome kami. Metode ini lebih cepat dan mudah.",
                "chrome_extension_step_1": "<b>Langkah 1:</b> Pasang ekstensi Chrome secara manual",
                "chrome_extension_step_2": "<b>Langkah 2:</b> Buka Warp.dev dan buat akun baru",
                "chrome_extension_step_3": "<b>Langkah 3:</b> Setelah membuat akun, klik tombol ekstensi pada halaman yang dialihkan",
                "chrome_extension_step_4": "<b>Langkah 4:</b> Ekstensi akan secara otomatis menambahkan akun ke program ini",

                # JSON extraction steps
                "step_1": "<b>Langkah 1:</b> Buka situs Warp dan masuk",
                "step_2": "<b>Langkah 2:</b> Buka konsol pengembang browser (F12)",
                "step_3": "<b>Langkah 3:</b> Pergi ke tab Console",
                "step_4": "<b>Langkah 4:</b> Tempel kode JavaScript di bawah ini ke konsol",
                "step_5": "<b>Langkah 5:</b> Tekan Enter",
                "step_6": "<b>Langkah 6:</b> Klik tombol yang muncul di halaman",
                "step_7": "<b>Langkah 7:</b> Tempel JSON yang disalin di sini",

                # Help
                "help_title": "📖 Pengelola Akun Warp - Panduan Pengguna",
                "help_what_is": "🎯 Apa Fungsi Perangkat Lunak Ini?",
                "help_what_is_content": "Anda dapat melihat sisa batas antar akun yang dibuat untuk menggunakan editor kode Warp.dev secara gratis dan dengan mudah beralih dengan menekan tombol mulai. Alat ini mencegah pemblokiran dengan menggunakan ID berbeda untuk setiap tindakan.",
                "help_how_works": "⚙️ Bagaimana Cara Kerjanya?",
                "help_how_works_content": "Aplikasi ini memodifikasi permintaan yang dibuat editor Warp menggunakan proxy. Operasi dijalankan menggunakan informasi akun yang Anda pilih dan ID pengguna yang berbeda.",
                "help_how_to_use": "📝 Cara Menggunakan?",
                "help_how_to_use_content": '''<b>Penyiapan Awal:</b><br>
Karena bekerja dengan proxy, pada peluncuran pertama Anda harus memasang sertifikat yang ditentukan ke dalam penyimpanan akar tepercaya di komputer Anda. Setelah menyelesaikan instruksi, buka editor Warp dan masuk ke akun apa pun. Anda harus masuk melalui editor terlebih dahulu.<br><br>

<b>Menambahkan Akun (2 Metode):</b><br>
<b>1. Ekstensi Chrome:</b> Pasang ekstensi kami ke Chrome. Setelah membuat akun di Warp.dev, tombol ekstensi muncul pada halaman yang dialihkan dan dalam satu klik akun ditambahkan otomatis.<br>
<b>2. Metode Manual:</b> Di halaman pembuatan akun, buka konsol dengan F12, tempel kode JavaScript, dan tempel JSON ke program.<br><br>

<b>Instalasi Ekstensi Chrome:</b><br>
Pasang ekstensi Chrome secara manual. Setelah terpasang, tombol penambahan akun otomatis muncul pada halaman warp.dev/logged_in/remote. Pada halaman logged_in biasa muncul tombol untuk memuat ulang halaman.<br><br>

<b>Penggunaan:</b><br>
Untuk menggunakan akun yang telah ditambahkan, aktifkan Proxy. Setelah aktif, Anda dapat mengaktifkan salah satu akun dengan tombol mulai dan terus memakai editor Warp. Tombol \"Segarkan Batas\" menampilkan batas akun secara langsung.''',

                # Certificate installation
                "cert_title": "🔒 Instalasi Sertifikat Proxy Diperlukan",
                "cert_explanation": '''Agar Warp Proxy berfungsi dengan baik, sertifikat mitmproxy harus ditambahkan ke Otoritas Sertifikat Root Tepercaya.

Proses ini hanya dilakukan sekali dan tidak memengaruhi keamanan sistem Anda.''',
                "cert_steps": "📋 Langkah Instalasi:",
                "cert_step_1": "<b>Langkah 1:</b> Klik tombol \"Buka Berkas Sertifikat\" di bawah",
                "cert_step_2": "<b>Langkah 2:</b> Klik ganda berkas yang terbuka",
                "cert_step_3": "<b>Langkah 3:</b> Klik tombol \"Install Certificate...\"",
                "cert_step_4": "<b>Langkah 4:</b> Pilih \"Local Machine\" dan klik \"Next\"",
                "cert_step_5": "<b>Langkah 5:</b> Pilih \"Place all certificates in the following store\"",
                "cert_step_6": "<b>Langkah 6:</b> Klik \"Browse\"",
                "cert_step_7": "<b>Langkah 7:</b> Pilih folder \"Trusted Root Certification Authorities\"",
                "cert_step_8": "<b>Langkah 8:</b> Klik tombol \"OK\" dan \"Next\"",
                "cert_step_9": "<b>Langkah 9:</b> Klik tombol \"Finish\"",
                "cert_path": "Berkas sertifikat: {}",

                # Automatic certificate installation
                "cert_creating": "🔒 Membuat sertifikat...",
                "cert_created_success": "✅ Berkas sertifikat berhasil dibuat",
                "cert_creation_failed": "❌ Gagal membuat sertifikat",
                "cert_installing": "🔒 Memeriksa instalasi sertifikat...",
                "cert_installed_success": "✅ Sertifikat berhasil dipasang otomatis",
                "cert_install_failed": "❌ Instalasi sertifikat gagal - Mungkin memerlukan hak administrator",
                "cert_install_error": "❌ Kesalahan instalasi sertifikat: {}",

                # Manual certificate installation dialog
                "cert_manual_title": "🔒 Instalasi Sertifikat Manual Diperlukan",
                "cert_manual_explanation": '''Instalasi sertifikat otomatis gagal.

Anda perlu memasang sertifikat secara manual. Proses ini hanya dilakukan sekali dan tidak memengaruhi keamanan sistem Anda.''',
                "cert_manual_path": "Lokasi berkas sertifikat:",
                "cert_manual_steps": '''<b>Langkah Instalasi Manual:</b><br><br>
<b>1.</b> Pergi ke jalur berkas di atas<br>
<b>2.</b> Klik ganda berkas <code>mitmproxy-ca-cert.cer</code><br>
<b>3.</b> Klik tombol \"Install Certificate...\"<br>
<b>4.</b> Pilih \"Local Machine\" lalu klik \"Next\"<br>
<b>5.</b> Pilih \"Place all certificates in the following store\"<br>
<b>6.</b> Klik \"Browse\" → pilih \"Trusted Root Certification Authorities\"<br>
<b>7.</b> Klik \"OK\" → \"Next\" → \"Finish\"''',
                "cert_open_folder": "📁 Buka Folder Sertifikat",
                "cert_manual_complete": "✅ Instalasi Selesai",

                # Messages
                "account_added_success": "Akun berhasil ditambahkan",
                "no_accounts_to_update": "Tidak ada akun untuk diperbarui",
                "updating_limits": "Memperbarui batas...",
                "processing_account": "Memproses: {}",
                "refreshing_token": "Menyegarkan token: {}",
                "accounts_updated": "{} akun diperbarui",
                "proxy_starting": "Memulai proxy...",
                "proxy_configuring": "Mengonfigurasi pengaturan proxy Windows...",
                "proxy_started": "Proxy dimulai: {}",
                "proxy_stopped": "Proxy dihentikan",
                "proxy_starting_account": "Memulai proxy dan mengaktifkan {}...",
                "activating_account": "Mengaktifkan akun: {}...",
                "token_refreshing": "Menyegarkan token: {}",
                "proxy_started_account_activated": "Proxy dimulai dan {} diaktifkan",
                "windows_proxy_config_failed": "Pengaturan proxy Windows gagal dikonfigurasi",
                "mitmproxy_start_failed": "Mitmproxy gagal dimulai - Periksa port 8080",
                "proxy_start_error": "Kesalahan memulai proxy: {}",
                "proxy_stop_error": "Kesalahan menghentikan proxy: {}",
                "account_not_found": "Akun tidak ditemukan",
                "account_banned_cannot_activate": "{} akun diblokir - tidak dapat diaktifkan",
                "account_activation_error": "Kesalahan aktivasi akun: {}",
                "token_refresh_in_progress": "Penyegaran token sedang berlangsung, mohon tunggu...",
                "token_refresh_error": "Kesalahan penyegaran token: {}",
                "account_activated": "{} akun diaktifkan",
                "account_activation_failed": "Akun gagal diaktifkan",
                "proxy_unexpected_stop": "Proxy berhenti secara tak terduga",
                "account_deactivated": "{} akun dinonaktifkan",
                "account_deleted": "{} akun dihapus",
                "token_renewed": "{} token diperbarui",
                "account_banned_detected": "⛔ {} akun diblokir!",
                "token_renewal_progress": "🔄 {}/{} token diperbarui",

                # Error messages
                "invalid_json": "Format JSON tidak valid",
                "email_not_found": "Email tidak ditemukan",
                "certificate_not_found": "Berkas sertifikat tidak ditemukan!",
                "file_open_error": "Kesalahan membuka berkas: {}",
                "proxy_start_failed": "Proxy tidak dapat dimulai - Periksa port 8080",
                "proxy_config_failed": "Pengaturan proxy Windows tidak dapat dikonfigurasi",
                "token_refresh_failed": "{} token gagal diperbarui",
                "account_delete_failed": "Akun tidak dapat dihapus",
                "proxy_unexpected_stop": "⚠️ Proxy berhenti secara tak terduga",
                "enable_proxy_first": "Aktifkan proxy terlebih dahulu untuk mengaktifkan akun",
                "limit_info_failed": "Informasi batas gagal diambil",
                "token_renewal_failed": "⚠️ {} token gagal diperbarui",
                "token_check_error": "❌ Kesalahan pemeriksaan token",

                # Confirmation messages
                "delete_account_confirm": "Apakah Anda yakin ingin menghapus akun '{}'?\n\nTindakan ini tidak dapat dibatalkan!",

                # Status bar messages
                "default_status": "Aktifkan Proxy dan klik tombol mulai pada akun untuk mulai menggunakan.",
                "default_status_debug": "Aktifkan Proxy dan klik tombol mulai pada akun untuk mulai menggunakan. (Mode Debug Aktif)",

                # Debug and console messages
                "stylesheet_load_error": "Gagal memuat stylesheet: {}",
                "health_update_error": "Kesalahan pembaruan status kesehatan: {}",
                "token_update_error": "Kesalahan pembaruan token: {}",
                "account_update_error": "Kesalahan pembaruan akun: {}",
                "active_account_set_error": "Kesalahan menetapkan akun aktif: {}",
                "active_account_clear_error": "Kesalahan menghapus akun aktif: {}",
                "account_delete_error": "Kesalahan menghapus akun: {}",
                "limit_info_update_error": "Kesalahan pembaruan informasi batas: {}",
            },

            "en": {
                # General
                "app_title": "Warp Account Manager",
                "yes": "Yes",
                "no": "No",
                "ok": "OK",
                "cancel": "Cancel",
                "close": "Close",
                "error": "Error",
                "success": "Success",
                "warning": "Warning",
                "info": "Info",

                # Buttons
                "proxy_start": "Start Proxy",
                "proxy_stop": "Stop Proxy",
                "proxy_active": "Proxy Active",
                "add_account": "Add Account",
                "refresh_limits": "Refresh Limits",
                "help": "Help",
                "activate": "🟢 Activate",
                "deactivate": "🔴 Deactivate",
                "delete_account": "🗑️ Delete Account",
                "create_account": "🌐 Create Account",
                "add": "Add",
                "copy_javascript": "📋 Copy JavaScript Code",
                "copied": "✅ Copied!",
                "copy_error": "❌ Error!",
                "open_certificate": "📁 Open Certificate File",
                "installation_complete": "✅ Installation Complete",

                # Table headers
                "current": "Current",
                "email": "Email",
                "status": "Status",
                "limit": "Limit",

                # Activation button texts
                "button_active": "ACTIVE",
                "button_inactive": "INACTIVE",
                "button_banned": "BAN",
                "button_start": "Start",
                "button_stop": "Stop",

                # Status messages
                "status_active": "Active",
                "status_banned": "BAN",
                "status_token_expired": "Token Expired",
                "status_proxy_active": " (Proxy Active)",
                "status_error": "Error",
                "status_na": "N/A",
                "status_not_updated": "Not Updated",
                "status_healthy": "healthy",
                "status_unhealthy": "unhealthy",
                "status_banned_key": "banned",

                # Add account
                "add_account_title": "Add Account",
                "add_account_instruction": "Paste account JSON data below:",
                "add_account_placeholder": "Paste JSON data here...",
                "how_to_get_json": "❓ How to get JSON data?",
                "how_to_get_json_close": "❌ Close",
                "json_info_title": "How to Get JSON Data?",

                # Add account dialog tabs
                "tab_manual": "Manual",
                "tab_auto": "Automatic",
                "manual_method_title": "Manual JSON Addition",
                "auto_method_title": "Automatic Addition with Chrome Extension",

                # Chrome extension description
                "chrome_extension_title": "🌐 Chrome Extension",
                "chrome_extension_description": "You can automatically add your accounts using our Chrome extension. This method is faster and easier.",
                "chrome_extension_step_1": "<b>Step 1:</b> Manually install the Chrome extension",
                "chrome_extension_step_2": "<b>Step 2:</b> Go to Warp.dev and create a new account",
                "chrome_extension_step_3": "<b>Step 3:</b> After creating account, click the extension button on the redirected page",
                "chrome_extension_step_4": "<b>Step 4:</b> Extension will automatically add the account to this program",

                # JSON extraction steps
                "step_1": "<b>Step 1:</b> Go to Warp website and login",
                "step_2": "<b>Step 2:</b> Open browser developer console (F12)",
                "step_3": "<b>Step 3:</b> Go to Console tab",
                "step_4": "<b>Step 4:</b> Paste the JavaScript code below into console",
                "step_5": "<b>Step 5:</b> Press Enter",
                "step_6": "<b>Step 6:</b> Click the button that appears on the page",
                "step_7": "<b>Step 7:</b> Paste the copied JSON here",

                # Help
                "help_title": "📖 Warp Account Manager - User Guide",
                "help_what_is": "🎯 What Does This Software Do?",
                "help_what_is_content": "You can view remaining limits between accounts you create to use Warp.dev code editor for free and easily switch between them by clicking the start button. It prevents you from getting banned by using different IDs for each operation.",
                "help_how_works": "⚙️ How Does It Work?",
                "help_how_works_content": "It modifies requests made by Warp editor using proxy. It performs operations using the information of the account you selected and different user IDs.",
                "help_how_to_use": "📝 How to Use?",
                "help_how_to_use_content": '''<b>Initial Setup:</b><br>
Since it works with proxy, you are expected to install the specified certificate in the trusted root certificate area on your computer at first launch. After completing the instructions, open Warp editor and login to any account. You must login to an account through the editor first.<br><br>

<b>Adding Accounts (2 Methods):</b><br>
<b>1. Chrome Extension:</b> Install our extension to Chrome. After creating account on Warp.dev, extension button appears on redirected page, one-click adds account automatically.<br>
<b>2. Manual Method:</b> On account creation page, open console with F12, paste JavaScript code and copy JSON to add to program.<br><br>

<b>Chrome Extension Installation:</b><br>
Manually install the Chrome extension. When extension is installed, automatic account addition button appears on warp.dev/logged_in/remote pages. On normal logged_in pages, a page refresh button appears.<br><br>

<b>Usage:</b><br>
To use the accounts you added to the software, you activate the Proxy. After the activation process, you can activate one of your accounts by clicking the start button and continue using the Warp editor. You can instantly see the limits between your accounts with the "Refresh Limits" button.''',

                # Certificate installation
                "cert_title": "🔒 Proxy Certificate Installation Required",
                "cert_explanation": '''For Warp Proxy to work properly, mitmproxy certificate needs to be added to trusted root certificate authorities.

This process is done only once and does not affect your system security.''',
                "cert_steps": "📋 Installation Steps:",
                "cert_step_1": "<b>Step 1:</b> Click the \"Open Certificate File\" button below",
                "cert_step_2": "<b>Step 2:</b> Double-click the opened file",
                "cert_step_3": "<b>Step 3:</b> Click \"Install Certificate...\" button",
                "cert_step_4": "<b>Step 4:</b> Select \"Local Machine\" and click \"Next\"",
                "cert_step_5": "<b>Step 5:</b> Select \"Place all certificates in the following store\"",
                "cert_step_6": "<b>Step 6:</b> Click \"Browse\" button",
                "cert_step_7": "<b>Step 7:</b> Select \"Trusted Root Certification Authorities\" folder",
                "cert_step_8": "<b>Step 8:</b> Click \"OK\" and \"Next\" buttons",
                "cert_step_9": "<b>Step 9:</b> Click \"Finish\" button",
                "cert_path": "Certificate file: {}",

                # Automatic certificate installation
                "cert_creating": "🔒 Creating certificate...",
                "cert_created_success": "✅ Certificate file created successfully",
                "cert_creation_failed": "❌ Certificate creation failed",
                "cert_installing": "🔒 Checking certificate installation...",
                "cert_installed_success": "✅ Certificate installed automatically",
                "cert_install_failed": "❌ Certificate installation failed - Administrator privileges may be required",
                "cert_install_error": "❌ Certificate installation error: {}",

                # Manual certificate installation dialog
                "cert_manual_title": "🔒 Manual Certificate Installation Required",
                "cert_manual_explanation": '''Automatic certificate installation failed.

You need to install the certificate manually. This process is done only once and does not affect your system security.''',
                "cert_manual_path": "Certificate file location:",
                "cert_manual_steps": '''<b>Manual Installation Steps:</b><br><br>
<b>1.</b> Go to the file path above<br>
<b>2.</b> Double-click the <code>mitmproxy-ca-cert.cer</code> file<br>
<b>3.</b> Click "Install Certificate..." button<br>
<b>4.</b> Select "Local Machine" and click "Next"<br>
<b>5.</b> Select "Place all certificates in the following store"<br>
<b>6.</b> Click "Browse" → Select "Trusted Root Certification Authorities"<br>
<b>7.</b> Click "OK" → "Next" → "Finish"''',
                "cert_open_folder": "📁 Open Certificate Folder",
                "cert_manual_complete": "✅ Installation Complete",

                # Messages
                "account_added_success": "Account added successfully",
                "no_accounts_to_update": "No accounts found to update",
                "updating_limits": "Updating limits...",
                "processing_account": "Processing: {}",
                "refreshing_token": "Refreshing token: {}",
                "accounts_updated": "{} accounts updated",
                "proxy_starting": "Starting proxy...",
                "proxy_configuring": "Configuring Windows proxy settings...",
                "proxy_started": "Proxy started: {}",
                "proxy_stopped": "Proxy stopped",
                "proxy_starting_account": "Starting proxy and activating {}...",
                "activating_account": "Activating account: {}...",
                "token_refreshing": "Refreshing token: {}",
                "proxy_started_account_activated": "Proxy started and {} activated",
                "windows_proxy_config_failed": "Windows proxy configuration failed",
                "mitmproxy_start_failed": "Mitmproxy failed to start - Check port 8080",
                "proxy_start_error": "Proxy start error: {}",
                "proxy_stop_error": "Proxy stop error: {}",
                "account_not_found": "Account not found",
                "account_banned_cannot_activate": "{} account is banned - cannot activate",
                "account_activation_error": "Account activation error: {}",
                "token_refresh_in_progress": "Token refresh in progress, please wait...",
                "token_refresh_error": "Token refresh error: {}",
                "account_activated": "{} account activated",
                "account_activation_failed": "Account activation failed",
                "proxy_unexpected_stop": "Proxy stopped unexpectedly",
                "account_deactivated": "{} account deactivated",
                "account_deleted": "{} account deleted",
                "token_renewed": "{} token renewed",
                "account_banned_detected": "⛔ {} account banned!",
                "token_renewal_progress": "🔄 {}/{} tokens renewed",

                # Error messages
                "invalid_json": "Invalid JSON format",
                "email_not_found": "Email not found",
                "certificate_not_found": "Certificate file not found!",
                "file_open_error": "File open error: {}",
                "proxy_start_failed": "Proxy could not be started - Check port 8080",
                "proxy_config_failed": "Windows proxy settings could not be configured",
                "token_refresh_failed": "{} token could not be renewed",
                "account_delete_failed": "Account could not be deleted",
                "proxy_unexpected_stop": "⚠️ Proxy stopped unexpectedly",
                "enable_proxy_first": "Start proxy first to activate account",
                "limit_info_failed": "Could not get limit information",
                "token_renewal_failed": "⚠️ {} token could not be renewed",
                "token_check_error": "❌ Token check error",

                # Confirmation messages
                "delete_account_confirm": "Are you sure you want to delete '{}' account?\n\nThis action cannot be undone!",

                # Status bar messages
                "default_status": "Enable Proxy and click the start button on accounts to start using.",
                "default_status_debug": "Enable Proxy and click the start button on accounts to start using. (Debug Mode Active)",

                # Debug and console messages
                "stylesheet_load_error": "Could not load stylesheet: {}",
                "health_update_error": "Health status update error: {}",
                "token_update_error": "Token update error: {}",
                "account_update_error": "Account update error: {}",
                "active_account_set_error": "Active account set error: {}",
                "active_account_clear_error": "Active account clear error: {}",
                "account_delete_error": "Account delete error: {}",
                "limit_info_update_error": "Limit info update error: {}",
            },
        }

        return translations

    def get_text(self, key, *args):
        """Retrieve translated text."""
        try:
            text = self.translations[self.current_language].get(key, key)
            if args:
                return text.format(*args)
            return text
        except Exception:
            return key

    def set_language(self, language_code):
        """Change the active language."""
        if language_code in self.translations:
            self.current_language = language_code
            return True
        return False

    def get_current_language(self):
        """Return the currently active language code."""
        return self.current_language

    def get_available_languages(self):
        """Return available language codes."""
        return list(self.translations.keys())


_language_manager = None


def get_language_manager():
    """Return the global language manager instance."""
    global _language_manager
    if _language_manager is None:
        _language_manager = LanguageManager()
    return _language_manager


def _(key, *args):
    """Convenience translation helper."""
    return get_language_manager().get_text(key, *args)
