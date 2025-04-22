function showNotification(title, message, duration = 3000) {
    const existingNotifications = document.querySelectorAll(".notification");
    existingNotifications.forEach(notification => {
        notification.classList.add("hide");
        setTimeout(() => notification.remove(), 300);
    });
    
    const notification = document.createElement("div");
    notification.className = "notification";
    notification.innerHTML = `
        <div class="notification-title">${title}</div>
        <div class="notification-message">${message}</div>
    `;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add("hide");
        setTimeout(() => notification.remove(), 300);
    }, duration);
}

// Add a watchdog function to detect and recover from potential issues
let reloadCount = 0;
let lastReloadTime = 0;
const reloadThreshold = 3; // Max reloads within the time window
const reloadTimeWindow = 60000; // 1 minute window

// Enhanced reload protection with more sophisticated detection
function setupReloadProtection() {
    const now = Date.now();
    const reloadKey = 'last_page_reload';
    const countKey = 'reload_count';
    
    let storedTime = parseInt(sessionStorage.getItem(reloadKey) || '0');
    let storedCount = parseInt(sessionStorage.getItem(countKey) || '0');
    
    // If last reload was within 5 seconds, increment counter
    if (now - storedTime < 5000) {
        storedCount++;
        sessionStorage.setItem(countKey, storedCount.toString());
    } else {
        // Reset counter if it's been a while
        if (now - storedTime > reloadTimeWindow) {
            storedCount = 0;
        }
    }
    
    sessionStorage.setItem(reloadKey, now.toString());
    
    // Add enhanced session stability
    if (storedCount >= reloadThreshold) {
        console.warn('Detected reload loop! Taking preventive measures...');
        
        // Add additional safeguards
        try {
            // Clear any potential problematic cache entries
            const cacheKeys = [
                'last_page_reload',
                'reload_count',
                'initialStatusChecked'
            ];
            
            // Store essential data before clearing
            const messages = document.getElementById('messages');
            const messageCount = messages ? messages.childElementCount : 0;
            
            if (messageCount === 0) {
                // Only reset session storage if we don't have messages to preserve
                // This prevents clearing during legitimate new sessions
                cacheKeys.forEach(key => {
                    if (key !== 'xar_chat_history') {
                        sessionStorage.removeItem(key);
                    }
                });
            }
            
            // Add a visible warning
            setTimeout(() => {
                showNotification(
                    "Improving Page Stability",
                    "The chat interface has been optimized for better performance.",
                    10000
                );
                
                // Disable memory-intensive features
                if (window.OPTIMIZATION) {
                    window.OPTIMIZATION.useStreaming = messageCount > 10 ? false : true;
                    window.OPTIMIZATION.maxResponseTokens = 256; // Reduce token limit
                }
                
                // Add a recovery class to the body
                document.body.classList.add('optimized-mode');
                
                // Reset the counter after some time
                setTimeout(() => {
                    sessionStorage.setItem(countKey, '0');
                }, 120000);
            }, 1000);
        } catch (e) {
            console.error("Error in reload protection:", e);
        }
    }
}

// Run the protection setup on page load
setupReloadProtection();

window.showNotification = showNotification;

// Add RAM usage monitoring to detect potential issues
let lastMemoryWarning = 0;
function monitorResourceUsage() {
    if (window.performance && window.performance.memory) {
        const memUsage = window.performance.memory.usedJSHeapSize;
        const memLimit = window.performance.memory.jsHeapSizeLimit;
        const memPercentage = (memUsage / memLimit) * 100;
        
        if (memPercentage > 80 && Date.now() - lastMemoryWarning > 60000) {
            console.warn(`High memory usage: ${memPercentage.toFixed(1)}% of available heap`);
            lastMemoryWarning = Date.now();
            
            // Take action to reduce memory pressure
            window.stopAllApiLoops();
            
            // Try to force garbage collection in debug mode
            if (window.gc) window.gc();
            
            // Notify user if memory is critically high
            if (memPercentage > 90) {
                showNotification(
                    "Performance Optimization",
                    "Optimizing memory usage for better performance.",
                    5000
                );
            }
        }
    }
}

// Run memory check periodically
if (window.performance && window.performance.memory) {
    setInterval(monitorResourceUsage, 30000);
}

// Add a utility to manage API calls and prevent redundant requests
const apiCallManager = {
    activeRequests: {},
    lastCallTimes: {},
    minInterval: 2000, // Minimum time between identical API calls
    
    // Check if a call with the same ID is already in progress or called too recently
    canMakeRequest: function(requestId) {
        const now = Date.now();
        const isActive = this.activeRequests[requestId];
        const lastCall = this.lastCallTimes[requestId] || 0;
        const tooRecent = now - lastCall < this.minInterval;
        
        if (isActive || tooRecent) {
            console.log(`Skipping API call ${requestId} - ${isActive ? 'already active' : 'called too recently'}`);
            return false;
        }
        
        return true;
    },
    
    // Start tracking a request
    startRequest: function(requestId) {
        this.activeRequests[requestId] = true;
        this.lastCallTimes[requestId] = Date.now();
    },
    
    // End tracking a request
    endRequest: function(requestId) {
        this.activeRequests[requestId] = false;
    },
    
    // Enhance API call manager with global throttling for all API requests
    globalLastApiTime: 0,
    globalMinInterval: 1000, // 1 second minimum between ANY API calls
    
    isGlobalThrottled: function() {
        const now = Date.now();
        const elapsed = now - this.globalLastApiTime;
        
        if (elapsed < this.globalMinInterval) {
            console.warn(`Global API throttle active: ${elapsed}ms since last request`);
            return true;
        }
        
        return false;
    },
    
    // Override the existing makeRequest method to include global throttling
    makeRequest: async function(requestId, apiCallFn) {
        // Check both specific request throttling and global throttling
        if (!this.canMakeRequest(requestId) || this.isGlobalThrottled()) {
            return null;
        }
        
        this.startRequest(requestId);
        this.globalLastApiTime = Date.now();
        
        try {
            return await apiCallFn();
        } finally {
            this.endRequest(requestId);
        }
    },
    
    // Enhance global API manager to detect and handle hanging requests
    monitorHangingRequests: function() {
        const now = Date.now();
        const hangingThreshold = 15000; // 15 seconds
        
        Object.entries(this.activeRequests).forEach(([requestId, isActive]) => {
            if (isActive) {
                const startTime = this.lastCallTimes[requestId] || 0;
                if (now - startTime > hangingThreshold) {
                    console.warn(`Request ${requestId} appears to be hanging (${now - startTime}ms). Cleaning up.`);
                    this.endRequest(requestId);
                }
            }
        });
    }
};

// Run hanging request monitor periodically
setInterval(() => apiCallManager.monitorHangingRequests(), 5000);

// Create a helper to stop any recurring API calls that might be running
window.stopAllApiLoops = function() {
    // Clear all timers that might be running
    const highestId = window.setTimeout(() => {}, 0);
    for (let i = 0; i < highestId; i++) {
        window.clearTimeout(i);
        window.clearInterval(i);
    }
    console.log("Cleared all potential timer loops");
};

// If page reload frequency is high, stop all API loops on load
const reloadFrequency = parseInt(sessionStorage.getItem('reload_count') || '0');
if (reloadFrequency > 1) {
    window.stopAllApiLoops();
}

// Export to window object for global access
window.apiCallManager = apiCallManager;
