#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import locale
import os

class LanguageManager:
    """Çok dilli destek yöneticisi"""

    def __init__(self):
        self.current_language = self.detect_system_language()
        self.translations = self.load_translations()

    def detect_system_language(self):
        """Sistem dilini otomatik tespit et"""
        try:
            # Sistem dilini al (Python 3.15 uyumlu)
            try:
                system_locale = locale.getlocale()[0]
            except:
                # Fallback için eski metod
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    system_locale = locale.getdefaultlocale()[0]

            if system_locale:
                # Türkçe veya Azerice ise Türkçe (büyük/küçük harf duyarsız)
                locale_lower = system_locale.lower()
                if (locale_lower.startswith(('tr', 'az')) or
                    'turkish' in locale_lower or
                    'türk' in locale_lower):
                    return 'tr'

            # Varsayılan olarak İngilizce
            return 'en'
        except:
            return 'en'

    def load_translations(self):
        """Çeviri dosyalarını yükle"""
        translations = {
            'tr': {
                # Genel
                'app_title': 'Warp Hesap Yöneticisi',
                'yes': 'Evet',
                'no': 'Hayır',
                'ok': 'Tamam',
                'cancel': 'İptal',
                'close': 'Kapat',
                'error': 'Hata',
                'success': 'Başarılı',
                'warning': 'Uyarı',
                'info': 'Bilgi',

                # Butonlar
                'proxy_start': 'Proxy Başlat',
                'proxy_stop': 'Proxy Durdur',
                'proxy_active': 'Proxy Aktif',
                'add_account': 'Hesap Ekle',
                'refresh_limits': 'Limitleri Yenile',
                'help': 'Yardım',
                'activate': '🟢 Aktif Et',
                'deactivate': '🔴 Deaktif Et',
                'delete_account': '🗑️ Hesabı Sil',
                'create_account': '🌐 Hesap Oluştur',
                'add': 'Ekle',
                'copy_javascript': '📋 JavaScript Kodunu Kopyala',
                'copied': '✅ Kopyalandı!',
                'copy_error': '❌ Hata!',
                'open_certificate': '📁 Sertifika Dosyasını Aç',
                'installation_complete': '✅ Kurulumu Tamamladım',

                # Tablo başlıkları
                'current': 'Güncel',
                'email': 'Email',
                'status': 'Durum',
                'limit': 'Limit',

                # Aktivasyon buton metinleri
                'button_active': 'AKTİF',
                'button_inactive': 'PASİF',
                'button_banned': 'BAN',
                'button_start': 'Başlat',
                'button_stop': 'Durdur',

                # Durum mesajları
                'status_active': 'Aktif',
                'status_banned': 'BAN',
                'status_token_expired': 'Token Süresi Dolmuş',
                'status_proxy_active': ' (Proxy Aktif)',
                'status_error': 'Hata',
                'status_na': 'N/A',
                'status_not_updated': 'Güncellenmedi',
                'status_healthy': 'healthy',
                'status_unhealthy': 'unhealthy',
                'status_banned_key': 'banned',

                # Hesap ekleme
                'add_account_title': 'Hesap Ekle',
                'add_account_instruction': 'Hesap JSON verilerini aşağıya yapıştırın:',
                'add_account_placeholder': 'JSON verilerini buraya yapıştırın...',
                'how_to_get_json': '❓ JSON bilgilerini nasıl alırım?',
                'how_to_get_json_close': '❌ Kapat',
                'json_info_title': 'JSON Bilgilerini Nasıl Alırım?',

                # Hesap ekleme diyalogu tabları
                'tab_manual': 'Manuel',
                'tab_auto': 'Otomatik',
                'manual_method_title': 'Manuel JSON Ekleme',
                'auto_method_title': 'Chrome Eklentisi ile Otomatik Ekleme',

                # Chrome eklentisi açıklaması
                'chrome_extension_title': '🌐 Chrome Eklentisi',
                'chrome_extension_description': 'Chrome eklentimizi kullanarak hesaplarınızı otomatik olarak ekleyebilirsiniz. Bu yöntem daha hızlı ve kolaydır.',
                'chrome_extension_step_1': '<b>Adım 1:</b> Chrome eklentisini manuel olarak yükleyin',
                'chrome_extension_step_2': '<b>Adım 2:</b> Warp.dev sitesine gidin ve yeni hesap oluşturun',
                'chrome_extension_step_3': '<b>Adım 3:</b> Hesap oluşturduktan sonra yönlendirilen sayfada eklenti butonuna tıklayın',
                'chrome_extension_step_4': '<b>Adım 4:</b> Eklenti hesabı otomatik olarak bu programa ekleyecektir',

                # JSON alma adımları
                'step_1': '<b>Adım 1:</b> Warp web sitesine gidin ve giriş yapın',
                'step_2': '<b>Adım 2:</b> Tarayıcı geliştirici konsolunu açın (F12)',
                'step_3': '<b>Adım 3:</b> Console sekmesine gidin',
                'step_4': '<b>Adım 4:</b> Aşağıdaki JavaScript kodunu konsola yapıştırın',
                'step_5': '<b>Adım 5:</b> Enter tuşuna basın',
                'step_6': '<b>Adım 6:</b> Sayfada çıkan butona tıklayın',
                'step_7': '<b>Adım 7:</b> Kopyalanan JSON\'u buraya yapıştırın',

                # Yardım
                'help_title': '📖 Warp Hesap Yöneticisi - Kullanım Kılavuzu',
                'help_what_is': '🎯 Bu Yazılım Ne İşe Yarar?',
                'help_what_is_content': 'Warp.dev kod editörünü ücretsiz şekilde kullanabilmek için oluşturacağınız hesaplar arasında kalan limitlerinizi görebilir ve kolayca başlat butonuyla geçiş yapabilirsiniz. Her işleminizde farklı ID kullanarak banlanmanızı engeller.',
                'help_how_works': '⚙️ Nasıl Çalışır?',
                'help_how_works_content': 'Proxy kullanarak Warp editörünün yaptığı istekleri değiştirir. Seçtiğiniz hesabın bilgilerini ve farklı kullanıcı ID\'lerini kullanarak işlemleri gerçekleştirir.',
                'help_how_to_use': '📝 Nasıl Kullanılır?',
                'help_how_to_use_content': '''<b>İlk Kurulum:</b><br>
Proxy ile çalıştığı için ilk açılışta size belirtilen sertifikayı bilgisayarınızda güvenilen kök sertifikası alanında kurmanız beklenir. Talimatları tamamladıktan sonra Warp editörünü açarak herhangi bir hesaba giriş yaparsınız. İlk başta editör üzerinden bir hesaba giriş yapmanız zorunludur.<br><br>

<b>Hesap Ekleme (2 Yöntem):</b><br>
<b>1. Chrome Eklentisi:</b> Eklentimizi Chrome'a kurun. Warp.dev'de hesap oluşturduktan sonra yönlendirilen sayfada eklenti butonu belirir, tek tıkla hesap otomatik eklenir.<br>
<b>2. Manuel Yöntem:</b> Hesap oluşturma sayfasında F12 ile konsolu açın, JavaScript kodunu yapıştırın ve JSON'u kopyalayıp programa ekleyin.<br><br>

<b>Chrome Eklentisi Kurulumu:</b><br>
Chrome eklentisini manuel olarak yükleyin. Eklenti kurulduğunda, warp.dev/logged_in/remote sayfalarında otomatik hesap ekleme butonu görünür. Normal logged_in sayfalarında ise sayfa yenileme butonu belirir.<br><br>

<b>Kullanım:</b><br>
Yazılım üzerine eklediğiniz hesapları kullanabilmek için Proxy\'yi etkinleştirirsiniz. Etkinleştirme işleminden sonra hesaplarınızdan birine başlat butonuna tıklayarak aktif edebilir ve Warp editörünü kullanmaya devam edebilirsiniz. "Limitleri Yenile" butonu ile hesaplarınız arasındaki limitleri anlık görebilirsiniz.''',

                # Sertifika kurulumu
                'cert_title': '🔒 Proxy Sertifikası Kurulumu Gerekli',
                'cert_explanation': '''Warp Proxy'nin düzgün çalışması için mitmproxy sertifikasının
güvenilen kök sertifika yetkilileri arasına eklenmesi gerekiyor.

Bu işlem sadece bir kez yapılır ve sistem güvenliğinizi etkilemez.''',
                'cert_steps': '📋 Kurulum Adımları:',
                'cert_step_1': '<b>Adım 1:</b> Aşağıdaki "Sertifika Dosyasını Aç" butonuna tıklayın',
                'cert_step_2': '<b>Adım 2:</b> Açılan dosyaya çift tıklayın',
                'cert_step_3': '<b>Adım 3:</b> "Sertifika Yükle..." butonuna tıklayın',
                'cert_step_4': '<b>Adım 4:</b> "Yerel Makine" seçin ve "İleri" butonuna tıklayın',
                'cert_step_5': '<b>Adım 5:</b> "Tüm sertifikaları aşağıdaki depoya yerleştir" seçin',
                'cert_step_6': '<b>Adım 6:</b> "Gözat" butonuna tıklayın',
                'cert_step_7': '<b>Adım 7:</b> "Güvenilen Kök Sertifika Yetkilileri" klasörünü seçin',
                'cert_step_8': '<b>Adım 8:</b> "Tamam" ve "İleri" butonlarına tıklayın',
                'cert_step_9': '<b>Adım 9:</b> "Son" butonuna tıklayın',
                'cert_path': 'Sertifika dosyası: {}',

                # Otomatik sertifika kurulumu
                'cert_creating': '🔒 Sertifika oluşturuluyor...',
                'cert_created_success': '✅ Sertifika dosyası başarıyla oluşturuldu',
                'cert_creation_failed': '❌ Sertifika oluşturulamadı',
                'cert_installing': '🔒 Sertifika kurulumu kontrol ediliyor...',
                'cert_installed_success': '✅ Sertifika otomatik kuruldu',
                'cert_install_failed': '❌ Sertifika kurulumu başarısız - Yönetici yetkisi gerekebilir',
                'cert_install_error': '❌ Sertifika kurulum hatası: {}',

                # Manuel sertifika kurulum dialogu
                'cert_manual_title': '🔒 Manuel Sertifika Kurulumu Gerekli',
                'cert_manual_explanation': '''Otomatik sertifika kurulumu başarısız oldu.

Sertifikayı manuel olarak kurmanız gerekiyor. Bu işlem sadece bir kez yapılır ve sistem güvenliğinizi etkilemez.''',
                'cert_manual_path': 'Sertifika dosyası konumu:',
                'cert_manual_steps': '''<b>Manuel Kurulum Adımları:</b><br><br>
<b>1.</b> Yukarıdaki dosya yoluna gidin<br>
<b>2.</b> <code>mitmproxy-ca-cert.cer</code> dosyasına çift tıklayın<br>
<b>3.</b> "Sertifika Yükle..." butonuna tıklayın<br>
<b>4.</b> "Yerel Makine" seçin ve "İleri" tıklayın<br>
<b>5.</b> "Tüm sertifikaları aşağıdaki depoya yerleştir" seçin<br>
<b>6.</b> "Gözat" → "Güvenilen Kök Sertifika Yetkilileri" seçin<br>
<b>7.</b> "Tamam" → "İleri" → "Son" tıklayın''',
                'cert_open_folder': '📁 Sertifika Klasörünü Aç',
                'cert_manual_complete': '✅ Kurulumu Tamamladım',

                # Mesajlar
                'account_added_success': 'Hesap başarıyla eklendi',
                'no_accounts_to_update': 'Güncellenecek hesap bulunamadı',
                'updating_limits': 'Limitler güncelleniyor...',
                'processing_account': 'İşleniyor: {}',
                'refreshing_token': 'Token yenileniyor: {}',
                'accounts_updated': '{} hesap güncellendi',
                'proxy_starting': 'Proxy başlatılıyor...',
                'proxy_configuring': 'Windows proxy ayarları yapılandırılıyor...',
                'proxy_started': 'Proxy başlatıldı: {}',
                'proxy_stopped': 'Proxy durduruldu',
                'proxy_starting_account': 'Proxy başlatılıyor ve {} aktif ediliyor...',
                'activating_account': 'Hesap aktif ediliyor: {}...',
                'token_refreshing': 'Token yenileniyor: {}',
                'proxy_started_account_activated': 'Proxy başlatıldı ve {} aktif edildi',
                'windows_proxy_config_failed': 'Windows proxy ayarları yapılandırılamadı',
                'mitmproxy_start_failed': 'Mitmproxy başlatılamadı - Port 8080 kontrol edin',
                'proxy_start_error': 'Proxy başlatma hatası: {}',
                'proxy_stop_error': 'Proxy durdurma hatası: {}',
                'account_not_found': 'Hesap bulunamadı',
                'account_banned_cannot_activate': '{} hesabı banlanmış - aktif edilemez',
                'account_activation_error': 'Aktif etme hatası: {}',
                'token_refresh_in_progress': 'Token yenileme devam ediyor, lütfen bekleyin...',
                'token_refresh_error': 'Token yenileme hatası: {}',
                'account_activated': '{} hesabı aktif edildi',
                'account_activation_failed': 'Hesap aktif edilemedi',
                'proxy_unexpected_stop': 'Proxy beklenmedik şekilde durduruldu',
                'account_activated': '{} hesabı aktif edildi',
                'account_deactivated': '{} hesabı deaktif edildi',
                'account_deleted': '{} hesabı silindi',
                'token_renewed': '{} tokeni yenilendi',
                'account_banned_detected': '⛔ {} hesabı banlandı!',
                'token_renewal_progress': '🔄 {}/{} token yenilendi',

                # Hata mesajları
                'invalid_json': 'Geçersiz JSON formatı',
                'email_not_found': 'Email bulunamadı',
                'account_not_found': 'Hesap bulunamadı',
                'certificate_not_found': 'Sertifika dosyası bulunamadı!',
                'file_open_error': 'Dosya açma hatası: {}',
                'proxy_start_failed': 'Proxy başlatılamadı - Port 8080 kontrol edin',
                'proxy_config_failed': 'Windows proxy ayarları yapılandırılamadı',
                'account_banned_cannot_activate': '{} hesabı banlanmış - aktif edilemez',
                'token_refresh_failed': '{} tokeni yenilenemedi',
                'account_delete_failed': 'Hesap silinemedi',
                'proxy_unexpected_stop': '⚠️ Proxy beklenmedik şekilde durduruldu',
                'enable_proxy_first': 'Hesap aktif etmek için önce proxy\'yi başlatın',
                'limit_info_failed': 'Limit bilgisi alınamadı',
                'token_renewal_failed': '⚠️ {} token yenilenemedi',
                'token_check_error': '❌ Token kontrol hatası',

                # Onay mesajları
                'delete_account_confirm': '\'{}\' hesabını silmek istediğinizden emin misiniz?\n\nBu işlem geri alınamaz!',

                # Durum çubuğu mesajları
                'default_status': 'Proxy Etkinleştirip başlat butonuna tıklayarak kullanmaya başlayabilirsiniz.',
                'default_status_debug': 'Proxy Etkinleştirip başlat butonuna tıklayarak kullanmaya başlayabilirsiniz. (Debug Modu Aktif)',

                # Debug ve konsol mesajları (bunlar değişmeyebilir ama tutarlılık için)
                'stylesheet_load_error': 'Stil dosyası yüklenemedi: {}',
                'health_update_error': 'Sağlık durumu güncelleme hatası: {}',
                'token_update_error': 'Token güncelleme hatası: {}',
                'account_update_error': 'Hesap güncelleme hatası: {}',
                'active_account_set_error': 'Aktif hesap ayarlama hatası: {}',
                'active_account_clear_error': 'Aktif hesap temizleme hatası: {}',
                'account_delete_error': 'Hesap silme hatası: {}',
                'limit_info_update_error': 'Limit bilgisi güncelleme hatası: {}',


            },

            'en': {
                # General
                'app_title': 'Warp Account Manager',
                'yes': 'Yes',
                'no': 'No',
                'ok': 'OK',
                'cancel': 'Cancel',
                'close': 'Close',
                'error': 'Error',
                'success': 'Success',
                'warning': 'Warning',
                'info': 'Info',

                # Buttons
                'proxy_start': 'Start Proxy',
                'proxy_stop': 'Stop Proxy',
                'proxy_active': 'Proxy Active',
                'add_account': 'Add Account',
                'refresh_limits': 'Refresh Limits',
                'help': 'Help',
                'activate': '🟢 Activate',
                'deactivate': '🔴 Deactivate',
                'delete_account': '🗑️ Delete Account',
                'create_account': '🌐 Create Account',
                'add': 'Add',
                'copy_javascript': '📋 Copy JavaScript Code',
                'copied': '✅ Copied!',
                'copy_error': '❌ Error!',
                'open_certificate': '📁 Open Certificate File',
                'installation_complete': '✅ Installation Complete',

                # Table headers
                'current': 'Current',
                'email': 'Email',
                'status': 'Status',
                'limit': 'Limit',

                # Activation button texts
                'button_active': 'ACTIVE',
                'button_inactive': 'INACTIVE',
                'button_banned': 'BAN',
                'button_start': 'Start',
                'button_stop': 'Stop',

                # Status messages
                'status_active': 'Active',
                'status_banned': 'BAN',
                'status_token_expired': 'Token Expired',
                'status_proxy_active': ' (Proxy Active)',
                'status_error': 'Error',
                'status_na': 'N/A',
                'status_not_updated': 'Not Updated',
                'status_healthy': 'healthy',
                'status_unhealthy': 'unhealthy',
                'status_banned_key': 'banned',

                # Add account
                'add_account_title': 'Add Account',
                'add_account_instruction': 'Paste account JSON data below:',
                'add_account_placeholder': 'Paste JSON data here...',
                'how_to_get_json': '❓ How to get JSON data?',
                'how_to_get_json_close': '❌ Close',
                'json_info_title': 'How to Get JSON Data?',

                # Add account dialog tabs
                'tab_manual': 'Manual',
                'tab_auto': 'Automatic',
                'manual_method_title': 'Manual JSON Addition',
                'auto_method_title': 'Automatic Addition with Chrome Extension',

                # Chrome extension description
                'chrome_extension_title': '🌐 Chrome Extension',
                'chrome_extension_description': 'You can automatically add your accounts using our Chrome extension. This method is faster and easier.',
                'chrome_extension_step_1': '<b>Step 1:</b> Manually install the Chrome extension',
                'chrome_extension_step_2': '<b>Step 2:</b> Go to Warp.dev and create a new account',
                'chrome_extension_step_3': '<b>Step 3:</b> After creating account, click the extension button on the redirected page',
                'chrome_extension_step_4': '<b>Step 4:</b> Extension will automatically add the account to this program',

                # JSON extraction steps
                'step_1': '<b>Step 1:</b> Go to Warp website and login',
                'step_2': '<b>Step 2:</b> Open browser developer console (F12)',
                'step_3': '<b>Step 3:</b> Go to Console tab',
                'step_4': '<b>Step 4:</b> Paste the JavaScript code below into console',
                'step_5': '<b>Step 5:</b> Press Enter',
                'step_6': '<b>Step 6:</b> Click the button that appears on the page',
                'step_7': '<b>Step 7:</b> Paste the copied JSON here',

                # Help
                'help_title': '📖 Warp Account Manager - User Guide',
                'help_what_is': '🎯 What Does This Software Do?',
                'help_what_is_content': 'You can view remaining limits between accounts you create to use Warp.dev code editor for free and easily switch between them by clicking the start button. It prevents you from getting banned by using different IDs for each operation.',
                'help_how_works': '⚙️ How Does It Work?',
                'help_how_works_content': 'It modifies requests made by Warp editor using proxy. It performs operations using the information of the account you selected and different user IDs.',
                'help_how_to_use': '📝 How to Use?',
                'help_how_to_use_content': '''<b>Initial Setup:</b><br>
Since it works with proxy, you are expected to install the specified certificate in the trusted root certificate area on your computer at first launch. After completing the instructions, open Warp editor and login to any account. You must login to an account through the editor first.<br><br>

<b>Adding Accounts (2 Methods):</b><br>
<b>1. Chrome Extension:</b> Install our extension to Chrome. After creating account on Warp.dev, extension button appears on redirected page, one-click adds account automatically.<br>
<b>2. Manual Method:</b> On account creation page, open console with F12, paste JavaScript code and copy JSON to add to program.<br><br>

<b>Chrome Extension Installation:</b><br>
Manually install the Chrome extension. When extension is installed, automatic account addition button appears on warp.dev/logged_in/remote pages. On normal logged_in pages, a page refresh button appears.<br><br>

<b>Usage:</b><br>
To use the accounts you added to the software, you activate the Proxy. After the activation process, you can activate one of your accounts by clicking the start button and continue using the Warp editor. You can instantly see the limits between your accounts with the "Refresh Limits" button.''',

                # Certificate installation
                'cert_title': '🔒 Proxy Certificate Installation Required',
                'cert_explanation': '''For Warp Proxy to work properly, mitmproxy certificate needs to be added to trusted root certificate authorities.

This process is done only once and does not affect your system security.''',
                'cert_steps': '📋 Installation Steps:',
                'cert_step_1': '<b>Step 1:</b> Click the "Open Certificate File" button below',
                'cert_step_2': '<b>Step 2:</b> Double-click the opened file',
                'cert_step_3': '<b>Step 3:</b> Click "Install Certificate..." button',
                'cert_step_4': '<b>Step 4:</b> Select "Local Machine" and click "Next"',
                'cert_step_5': '<b>Step 5:</b> Select "Place all certificates in the following store"',
                'cert_step_6': '<b>Step 6:</b> Click "Browse" button',
                'cert_step_7': '<b>Step 7:</b> Select "Trusted Root Certification Authorities" folder',
                'cert_step_8': '<b>Step 8:</b> Click "OK" and "Next" buttons',
                'cert_step_9': '<b>Step 9:</b> Click "Finish" button',
                'cert_path': 'Certificate file: {}',

                # Automatic certificate installation
                'cert_creating': '🔒 Creating certificate...',
                'cert_created_success': '✅ Certificate file created successfully',
                'cert_creation_failed': '❌ Certificate creation failed',
                'cert_installing': '🔒 Checking certificate installation...',
                'cert_installed_success': '✅ Certificate installed automatically',
                'cert_install_failed': '❌ Certificate installation failed - Administrator privileges may be required',
                'cert_install_error': '❌ Certificate installation error: {}',

                # Manual certificate installation dialog
                'cert_manual_title': '🔒 Manual Certificate Installation Required',
                'cert_manual_explanation': '''Automatic certificate installation failed.

You need to install the certificate manually. This process is done only once and does not affect your system security.''',
                'cert_manual_path': 'Certificate file location:',
                'cert_manual_steps': '''<b>Manual Installation Steps:</b><br><br>
<b>1.</b> Go to the file path above<br>
<b>2.</b> Double-click the <code>mitmproxy-ca-cert.cer</code> file<br>
<b>3.</b> Click "Install Certificate..." button<br>
<b>4.</b> Select "Local Machine" and click "Next"<br>
<b>5.</b> Select "Place all certificates in the following store"<br>
<b>6.</b> Click "Browse" → Select "Trusted Root Certification Authorities"<br>
<b>7.</b> Click "OK" → "Next" → "Finish"''',
                'cert_open_folder': '📁 Open Certificate Folder',
                'cert_manual_complete': '✅ Installation Complete',

                # Messages
                'account_added_success': 'Account added successfully',
                'no_accounts_to_update': 'No accounts found to update',
                'updating_limits': 'Updating limits...',
                'processing_account': 'Processing: {}',
                'refreshing_token': 'Refreshing token: {}',
                'accounts_updated': '{} accounts updated',
                'proxy_starting': 'Starting proxy...',
                'proxy_configuring': 'Configuring Windows proxy settings...',
                'proxy_started': 'Proxy started: {}',
                'proxy_stopped': 'Proxy stopped',
                'proxy_starting_account': 'Starting proxy and activating {}...',
                'activating_account': 'Activating account: {}...',
                'token_refreshing': 'Refreshing token: {}',
                'proxy_started_account_activated': 'Proxy started and {} activated',
                'windows_proxy_config_failed': 'Windows proxy configuration failed',
                'mitmproxy_start_failed': 'Mitmproxy failed to start - Check port 8080',
                'proxy_start_error': 'Proxy start error: {}',
                'proxy_stop_error': 'Proxy stop error: {}',
                'account_not_found': 'Account not found',
                'account_banned_cannot_activate': '{} account is banned - cannot activate',
                'account_activation_error': 'Account activation error: {}',
                'token_refresh_in_progress': 'Token refresh in progress, please wait...',
                'token_refresh_error': 'Token refresh error: {}',
                'account_activated': '{} account activated',
                'account_activation_failed': 'Account activation failed',
                'proxy_unexpected_stop': 'Proxy stopped unexpectedly',
                'account_activated': '{} account activated',
                'account_deactivated': '{} account deactivated',
                'account_deleted': '{} account deleted',
                'token_renewed': '{} token renewed',
                'account_banned_detected': '⛔ {} account banned!',
                'token_renewal_progress': '🔄 {}/{} tokens renewed',

                # Error messages
                'invalid_json': 'Invalid JSON format',
                'email_not_found': 'Email not found',
                'account_not_found': 'Account not found',
                'certificate_not_found': 'Certificate file not found!',
                'file_open_error': 'File open error: {}',
                'proxy_start_failed': 'Proxy could not be started - Check port 8080',
                'proxy_config_failed': 'Windows proxy settings could not be configured',
                'account_banned_cannot_activate': '{} account is banned - cannot be activated',
                'token_refresh_failed': '{} token could not be renewed',
                'account_delete_failed': 'Account could not be deleted',
                'proxy_unexpected_stop': '⚠️ Proxy stopped unexpectedly',
                'enable_proxy_first': 'Start proxy first to activate account',
                'limit_info_failed': 'Could not get limit information',
                'token_renewal_failed': '⚠️ {} token could not be renewed',
                'token_check_error': '❌ Token check error',

                # Confirmation messages
                'delete_account_confirm': 'Are you sure you want to delete \'{}\' account?\n\nThis action cannot be undone!',

                # Status bar messages
                'default_status': 'Enable Proxy and click the start button on accounts to start using.',
                'default_status_debug': 'Enable Proxy and click the start button on accounts to start using. (Debug Mode Active)',

                # Debug and console messages (these might not change but for consistency)
                'stylesheet_load_error': 'Could not load stylesheet: {}',
                'health_update_error': 'Health status update error: {}',
                'token_update_error': 'Token update error: {}',
                'account_update_error': 'Account update error: {}',
                'active_account_set_error': 'Active account set error: {}',
                'active_account_clear_error': 'Active account clear error: {}',
                'account_delete_error': 'Account delete error: {}',
                'limit_info_update_error': 'Limit info update error: {}',


            }
        }

        return translations

    def get_text(self, key, *args):
        """Çeviri metnini al"""
        try:
            text = self.translations[self.current_language].get(key, key)
            if args:
                return text.format(*args)
            return text
        except:
            return key

    def set_language(self, language_code):
        """Dili değiştir"""
        if language_code in self.translations:
            self.current_language = language_code
            return True
        return False

    def get_current_language(self):
        """Mevcut dili döndür"""
        return self.current_language

    def get_available_languages(self):
        """Kullanılabilir dilleri döndür"""
        return list(self.translations.keys())

# Global dil yöneticisi instance'ı
_language_manager = None

def get_language_manager():
    """Global dil yöneticisini al"""
    global _language_manager
    if _language_manager is None:
        _language_manager = LanguageManager()
    return _language_manager

def _(key, *args):
    """Kısa çeviri fonksiyonu"""
    return get_language_manager().get_text(key, *args)
