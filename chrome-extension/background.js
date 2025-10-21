// Background script for Warp Account Bridge
// Handles extension lifecycle and bridge communication

const BRIDGE_CONFIG = {
  pythonAppPort: 8765,
  extensionId: "warp-account-bridge-v1",
};

// Check if Python app is running
async function checkPythonApp() {
  try {
    const response = await fetch(`http://localhost:${BRIDGE_CONFIG.pythonAppPort}/health`, {
      method: "GET",
      headers: {
        "X-Extension-ID": BRIDGE_CONFIG.extensionId,
      },
    });
    return response.ok;
  } catch (error) {
    return false;
  }
}

// Setup bridge configuration on Python app
async function setupBridge() {
  try {
    const response = await fetch(`http://localhost:${BRIDGE_CONFIG.pythonAppPort}/setup-bridge`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Extension-ID": BRIDGE_CONFIG.extensionId,
      },
      body: JSON.stringify({
        extensionId: chrome.runtime.id,
        version: chrome.runtime.getManifest().version,
      }),
    });

    if (response.ok) {
      console.log("Bridge setup successful");
      return true;
    } else {
      console.log("Bridge setup failed:", await response.text());
      return false;
    }
  } catch (error) {
    console.log("Bridge setup error:", error);
    return false;
  }
}

// Extension installed/startup
chrome.runtime.onInstalled.addListener(async (details) => {
  console.log("Warp Account Bridge installed/updated");

  // Try to setup bridge with Python app
  setTimeout(async () => {
    const isAppRunning = await checkPythonApp();
    if (isAppRunning) {
      await setupBridge();
    }
  }, 2000);
});

// Extension startup
chrome.runtime.onStartup.addListener(async () => {
  console.log("Warp Account Bridge started");

  // Try to setup bridge with Python app
  setTimeout(async () => {
    const isAppRunning = await checkPythonApp();
    if (isAppRunning) {
      await setupBridge();
    }
  }, 2000);
});

// Handle messages from content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === "EXTRACT_ACCOUNT_DATA") {
    // This could be used for alternative data extraction if needed
    handleAccountDataExtraction(request, sender, sendResponse);
    return true; // Will respond asynchronously
  } else if (request.type === "CHECK_PYTHON_APP") {
    checkPythonApp().then(sendResponse);
    return true;
  }
});

// Handle account data extraction (alternative method)
async function handleAccountDataExtraction(request, sender, sendResponse) {
  try {
    // Execute script in the content script's context to extract data
    const results = await chrome.scripting.executeScript({
      target: { tabId: sender.tab.id },
      func: extractFirebaseData,
    });

    if (results && results[0] && results[0].result) {
      sendResponse({ success: true, data: results[0].result });
    } else {
      sendResponse({ success: false, error: "No data found" });
    }
  } catch (error) {
    sendResponse({ success: false, error: error.message });
  }
}

// Function to inject into page for data extraction
function extractFirebaseData() {
  return new Promise((resolve, reject) => {
    try {
      const request = indexedDB.open("firebaseLocalStorageDb");

      request.onsuccess = function (event) {
        const db = event.target.result;
        const transaction = db.transaction(["firebaseLocalStorage"], "readonly");
        const objectStore = transaction.objectStore("firebaseLocalStorage");

        objectStore.getAll().onsuccess = function (event) {
          const results = event.target.result;

          for (let result of results) {
            if (result.value && typeof result.value === "object" && result.value.email && result.value.stsTokenManager) {
              resolve(result.value);
              return;
            }
          }
          reject(new Error("No valid account data found"));
        };

        objectStore.getAll().onerror = () => reject(new Error("Database read error"));
      };

      request.onerror = () => reject(new Error("Database connection error"));
    } catch (error) {
      reject(error);
    }
  });
}

// Monitor tab changes to detect warp.dev visits
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.url && tab.url.includes("app.warp.dev/logged_in")) {
    // Check if Python app is running when user visits the target page
    const isAppRunning = await checkPythonApp();
    if (!isAppRunning) {
      // Could show a notification here if needed
      console.log("Python app not running when visiting Warp page");
    }
  }
});

// Periodic health check (every 5 minutes)
setInterval(async () => {
  const isAppRunning = await checkPythonApp();
  if (isAppRunning) {
    // Ensure bridge is properly configured
    await setupBridge();
  }
}, 300000); // 5 minutes
