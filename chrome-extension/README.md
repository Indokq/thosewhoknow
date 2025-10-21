# Warp Account Bridge - Chrome Extension

Bu Chrome eklentisi Warp hesap verilerini otomatik olarak Python uygulamasına aktarmak için kullanılır.

## Kurulum

1. Chrome'da `chrome://extensions/` adresine gidin
2. Sağ üst köşeden "Developer mode" açın
3. "Load unpacked" butonuna tıklayın
4. Bu klasörü (`chrome-extension`) seçin

## Kullanım

1. Python uygulamasını çalıştırın (Bridge server otomatik başlar)
2. Chrome'da `https://app.warp.dev/logged_in/remote` sayfasına gidin
3. Sayfada "📡 Add to Warp Manager" butonu görünecek
4. Butona tıklayarak hesap verilerini otomatik aktarın

## Özellikler

- ✅ Otomatik veri çıkarma
- ✅ Güvenli bridge iletişimi
- ✅ Sabit extension ID
- ✅ Hata yönetimi
- ✅ Görsel geri bildirim

## Teknik Detaylar

- **Port**: 8765 (Python uygulaması)
- **Extension ID**: `warp-account-bridge-v1`
- **Target Page**: `app.warp.dev/logged_in/remote`
- **Data Source**: IndexedDB (firebaseLocalStorageDb)

## Dosyalar

- `manifest.json`: Extension configuration
- `content.js`: Page injection script
- `background.js`: Extension lifecycle management
