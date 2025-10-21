// Content script for Warp Account Bridge
// Runs on https://app.warp.dev/logged_in/remote pages

const BRIDGE_CONFIG = {
  pythonAppPort: 8765,
  extensionId: "warp-account-bridge-v1",
};

let bridgeButton = null;
let isDataExtracted = false;
let isProcessing = false;

// Check if we can extract data
async function checkDataAvailability() {
  try {
    const request = indexedDB.open("firebaseLocalStorageDb");

    return new Promise((resolve) => {
      request.onsuccess = function (event) {
        const db = event.target.result;
        const transaction = db.transaction(["firebaseLocalStorage"], "readonly");
        const objectStore = transaction.objectStore("firebaseLocalStorage");

        objectStore.getAll().onsuccess = function (event) {
          const results = event.target.result;
          const hasValidData = results.some((item) => item.value && typeof item.value === "object" && item.value.email && item.value.stsTokenManager);
          resolve(hasValidData);
        };

        objectStore.getAll().onerror = () => resolve(false);
      };

      request.onerror = () => resolve(false);
    });
  } catch (error) {
    console.log("Data check error:", error);
    return false;
  }
}

// Extract account data
async function extractAccountData() {
  try {
    const request = indexedDB.open("firebaseLocalStorageDb");

    return new Promise((resolve, reject) => {
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
    });
  } catch (error) {
    throw new Error(`Data extraction failed: ${error.message}`);
  }
}

// Send data to Python app
async function sendDataToPythonApp(accountData) {
  try {
    console.log("Sending account data to bridge server...");
    const response = await fetch(`http://localhost:${BRIDGE_CONFIG.pythonAppPort}/add-account`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Extension-ID": BRIDGE_CONFIG.extensionId,
      },
      body: JSON.stringify(accountData),
    });

    if (response.ok) {
      const result = await response.json();
      console.log("Account successfully sent to bridge server");
      return { success: true, message: result.message || "Account added successfully" };
    } else {
      const error = await response.text();
      console.error("Bridge server returned error:", error);
      return { success: false, message: `Server error: ${error}` };
    }
  } catch (error) {
    console.error("Bridge connection error:", error);
    if (error.message.includes("Failed to fetch") || error.message.includes("ERR_CONNECTION_REFUSED")) {
      return { success: false, message: "Bridge server not running. Please start Warp Account Manager first!" };
    }
    return { success: false, message: `Connection failed: ${error.message}` };
  }
}

// Create and show bridge button
function createBridgeButton() {
  if (bridgeButton) return;

  bridgeButton = document.createElement("div");
  bridgeButton.id = "warp-bridge-button";
  bridgeButton.innerHTML = `
    <div style="
      position: fixed;
      top: 20px;
      left: 50%;
      transform: translateX(-50%);
      z-index: 10000;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 6px 12px;
      border-radius: 4px;
      cursor: pointer;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 11px;
      font-weight: 500;
      box-shadow: 0 2px 8px rgba(0,0,0,0.15);
      transition: all 0.2s ease;
      border: none;
      user-select: none;
      display: flex;
      align-items: center;
      gap: 4px;
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255,255,255,0.1);
    " onmouseover="this.style.transform='translateX(-50%) translateY(-1px)'; this.style.boxShadow='0 4px 12px rgba(0,0,0,0.2)'"
       onmouseout="this.style.transform='translateX(-50%)'; this.style.boxShadow='0 2px 8px rgba(0,0,0,0.15)'"
       onclick="this.querySelector('.text').textContent='Processing...'; this.style.pointerEvents='none';">
      <div style="width: 8px; height: 8px; background: #fff; border-radius: 50%; opacity: 0.8;"></div>
      <div class="text">Add to Warp Manager</div>
    </div>
  `;

  bridgeButton.addEventListener("click", handleButtonClick);
  document.body.appendChild(bridgeButton);
}

// Handle button click
async function handleButtonClick() {
  // Prevent multiple simultaneous clicks
  if (isProcessing || bridgeButton.style.pointerEvents === "none") {
    console.log("Already processing or button disabled");
    return;
  }

  // Set processing flag immediately
  isProcessing = true;

  const buttonText = bridgeButton.querySelector(".text");
  const originalText = buttonText.textContent;

  // Disable button immediately
  bridgeButton.style.pointerEvents = "none";

  try {
    console.log("Starting account extraction process...");
    buttonText.textContent = "Extracting data...";

    // Check data availability first
    const hasData = await checkDataAvailability();
    if (!hasData) {
      throw new Error("No account data available");
    }

    const accountData = await extractAccountData();
    console.log("Account data extracted successfully");

    buttonText.textContent = "Sending to app...";
    const result = await sendDataToPythonApp(accountData);

    if (result.success) {
      console.log("Account added successfully via bridge");
      buttonText.textContent = "✅ Added successfully!";
      bridgeButton.style.background = "linear-gradient(135deg, #4CAF50 0%, #45a049 100%)";
      isDataExtracted = true;

      // Save extraction state to localStorage with session-specific keys
      const urlParams = new URLSearchParams(window.location.search);
      const apiKey = urlParams.get("apiKey") || "default";
      const oobCode = urlParams.get("oobCode") || "default";
      const sessionKey = `warp_session_${apiKey}_${oobCode}`;

      localStorage.setItem(`${sessionKey}_time`, Date.now().toString());
      localStorage.setItem(`${sessionKey}_email`, accountData.email || "unknown");
      console.log(`Session cache set: ${sessionKey} -> ${accountData.email || "unknown"}`);

      // Hide button after 3 seconds
      setTimeout(() => {
        if (bridgeButton) {
          bridgeButton.style.opacity = "0";
          setTimeout(() => {
            if (bridgeButton && bridgeButton.parentNode) {
              bridgeButton.parentNode.removeChild(bridgeButton);
              bridgeButton = null;
            }
            // Reset processing flag after cleanup
            isProcessing = false;
          }, 300);
        }
      }, 3000);
    } else {
      throw new Error(result.message);
    }
  } catch (error) {
    console.error("Bridge error:", error);
    buttonText.textContent = "❌ Error: " + error.message;
    bridgeButton.style.background = "linear-gradient(135deg, #f44336 0%, #d32f2f 100%)";

    // Reset button after 5 seconds
    setTimeout(() => {
      if (bridgeButton) {
        buttonText.textContent = originalText;
        bridgeButton.style.background = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)";
        bridgeButton.style.pointerEvents = "auto";
      }
      // Reset processing flag
      isProcessing = false;
    }, 5000);
  }
}

// Initialize bridge
async function initBridge() {
  // Wait for page to be fully loaded
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initBridge);
    return;
  }

  // Remove existing button if any
  if (bridgeButton && bridgeButton.parentNode) {
    bridgeButton.parentNode.removeChild(bridgeButton);
    bridgeButton = null;
  }

  // Check which page we're on and show appropriate button
  const currentUrl = window.location.href;

  console.log(`Current URL: ${currentUrl}`);

  // Clear old global cache entries (migration)
  const oldKeys = ["warp_account_extracted", "warp_account_extracted_time", "warp_account_extracted_email"];
  oldKeys.forEach((key) => {
    if (localStorage.getItem(key)) {
      localStorage.removeItem(key);
      console.log(`Cleared old global cache: ${key}`);
    }
  });

  if (currentUrl.includes("app.warp.dev/logged_in") || currentUrl.includes("app.warp.dev/login")) {
    // All logged in pages - show bridge button
    console.log("Logged in page detected - checking for account data...");

    // Wait a bit for the page to settle and check multiple times
    let attempts = 0;
    const maxAttempts = 5;

    const checkAndShow = async () => {
      try {
        // Generate unique key for this session/URL
        const urlParams = new URLSearchParams(window.location.search);
        const apiKey = urlParams.get("apiKey") || "default";
        const oobCode = urlParams.get("oobCode") || "default";
        const sessionKey = `warp_session_${apiKey}_${oobCode}`;

        // Check if this specific session was already processed
        const lastExtracted = localStorage.getItem(`${sessionKey}_time`);
        const lastEmail = localStorage.getItem(`${sessionKey}_email`);

        // Clear old cache entries (older than 1 hour)
        const cutoffTime = Date.now() - 60 * 60 * 1000;
        for (let i = localStorage.length - 1; i >= 0; i--) {
          const key = localStorage.key(i);
          if (key && key.startsWith("warp_session_") && key.endsWith("_time")) {
            const time = localStorage.getItem(key);
            if (time && parseInt(time) < cutoffTime) {
              localStorage.removeItem(key);
              localStorage.removeItem(key.replace("_time", "_email"));
              console.log(`Cleared old cache for ${key}`);
            }
          }
        }

        if (lastExtracted && Date.now() - parseInt(lastExtracted) < 5 * 60 * 1000) {
          console.log(`This session was recently processed (${lastEmail || "unknown"}), skipping button creation`);
          return false;
        }

        console.log(`Checking data availability (attempt ${attempts + 1}/${maxAttempts})...`);
        const hasData = await checkDataAvailability();
        console.log(`Data available: ${hasData}, isDataExtracted: ${isDataExtracted}, bridgeButton exists: ${!!bridgeButton}`);

        if (hasData && !isDataExtracted && !bridgeButton) {
          console.log("Creating bridge button...");
          createBridgeButton();
          return true;
        } else if (!hasData && attempts < maxAttempts) {
          attempts++;
          setTimeout(checkAndShow, 1000);
        } else {
          console.log("Stopping attempts - either data not available or max attempts reached");
        }
      } catch (error) {
        console.log("Bridge init error:", error);
        if (attempts < maxAttempts) {
          attempts++;
          setTimeout(checkAndShow, 1000);
        }
      }
      return false;
    };

    setTimeout(checkAndShow, 2000);
  }
}

// Start the bridge
initBridge();

// Also listen for navigation changes (SPA)
let lastUrl = location.href;
new MutationObserver(() => {
  const url = location.href;
  if (url !== lastUrl) {
    lastUrl = url;
    // Page changed, reinitialize if needed
    setTimeout(initBridge, 1000);
  }
}).observe(document, { subtree: true, childList: true });
