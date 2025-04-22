document.addEventListener("DOMContentLoaded", () => {
    const API_URL = "http://localhost:5000";
    const userInput = document.getElementById("userinput");
    const sendBtn = document.getElementById("sendbtn");
    const voiceBtn = document.getElementById("voiceBtn");
    const messages = document.getElementById("messages");
    const xarTitleContainer = document.getElementById("xar-title-container");

    const OPTIMIZATION = {
        useStreaming: true,
        maxResponseTokens: 3072, // Increased from 512 to 3072 (6x)
        streamChunkSize: 10,
        chunkBufferThreshold: 25,
        streamTimeout: 60000, // 60 second timeout for streams
        maxStreamErrors: 3 // Maximum consecutive errors before falling back
    };

    const domCache = {
        messages: document.getElementById("messages"),
        sendBtn: document.getElementById("sendbtn")
    };

    const addClass = (element, className) => element.className += ` ${className}`;
    const removeClass = (element, className) => {
        element.className = element.className.replace(
            new RegExp(`(?:^|\\s)${className}(?!\\S)`, 'g'), ''
        ).trim();
    };

    userInput.addEventListener('focus', () => {
        if (messages.childElementCount === 0) {
            xarTitleContainer.classList.add('minimized');
        }
    });

    userInput.addEventListener('input', () => {
        if (!xarTitleContainer.classList.contains('minimized')) {
            xarTitleContainer.classList.add('minimized');
        }
    });

    function handleXarTitleVisibility() {
        if (messages.childElementCount > 0) {
            if (!xarTitleContainer.classList.contains('minimized')) {
                xarTitleContainer.classList.add('minimized');
            }
        } else {
            xarTitleContainer.classList.remove('minimized');
        }
    }

    let recognition = null;
    let isRecording = false;
    let silenceTimeout = null;

    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        const voiceWave1 = document.createElement('div');
        const voiceWave2 = document.createElement('div');
        const voiceWave3 = document.createElement('div');
        voiceWave1.className = 'voice-wave';
        voiceWave2.className = 'voice-wave';
        voiceWave3.className = 'voice-wave';
        voiceBtn.appendChild(voiceWave1);
        voiceBtn.appendChild(voiceWave2);
        voiceBtn.appendChild(voiceWave3);

        recognition.onresult = (event) => {
            const transcript = Array.from(event.results)
                .map(result => result[0].transcript)
                .join('');
            userInput.value = transcript;
            if (silenceTimeout) {
                clearTimeout(silenceTimeout);
                silenceTimeout = null;
            }
            userInput.style.height = 'auto';
            const newHeight = Math.min(userInput.scrollHeight, 200);
            userInput.style.height = newHeight + 'px';
        };

        recognition.onspeechend = () => {
            if (silenceTimeout) clearTimeout(silenceTimeout);
            silenceTimeout = setTimeout(() => {
                if (isRecording) {
                    recognition.stop();
                }
            }, 1500);
        };

        recognition.onend = () => {
            isRecording = false;
            voiceBtn.classList.remove('recording');
            voiceBtn.innerHTML = '<i class="ri-mic-line"></i>';
            voiceBtn.appendChild(voiceWave1);
            voiceBtn.appendChild(voiceWave2);
            voiceBtn.appendChild(voiceWave3);
            if (silenceTimeout) {
                clearTimeout(silenceTimeout);
                silenceTimeout = null;
            }
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            isRecording = false;
            voiceBtn.classList.remove('recording');
            voiceBtn.innerHTML = '<i class="ri-mic-line"></i>';
            if (silenceTimeout) {
                clearTimeout(silenceTimeout);
                silenceTimeout = null;
            }
            const errorMessage = event.error === 'not-allowed' ? 
                'Microphone permission denied. Please allow microphone access.' : 
                'Speech recognition error. Please try again.';
            showNotification('Error', errorMessage);
            voiceBtn.appendChild(voiceWave1);
            voiceBtn.appendChild(voiceWave2);
            voiceBtn.appendChild(voiceWave3);
        };

        voiceBtn.addEventListener('click', () => {
            if (isRecording) {
                if (silenceTimeout) {
                    clearTimeout(silenceTimeout);
                    silenceTimeout = null;
                }
                recognition.stop();
                isRecording = false;
                voiceBtn.classList.remove('recording');
                voiceBtn.innerHTML = '<i class="ri-mic-line"></i>';
                voiceBtn.appendChild(voiceWave1);
                voiceBtn.appendChild(voiceWave2);
                voiceBtn.appendChild(voiceWave3);
            } else {
                userInput.value = '';
                userInput.style.height = 'auto';
                recognition.start();
                isRecording = true;
                voiceBtn.classList.add('recording');
                voiceBtn.innerHTML = '<i class="ri-mic-fill"></i>';
                voiceBtn.appendChild(voiceWave1);
                voiceBtn.appendChild(voiceWave2);
                voiceBtn.appendChild(voiceWave3);
            }
        });
    } else {
        voiceBtn.style.display = 'none';
        console.log('Speech recognition not supported in this browser.');
    }

    function showNotification(title, message) {
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
        }, 3000);
    }

    async function checkServerStatus() {
        try {
            console.log("Performing initial server status check...");
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 3000);
            const response = await fetch(`${API_URL}/status`, {
                method: "GET",
                headers: { "Content-Type": "application/json" },
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            if (response.ok) {
                const data = await response.json();
                console.log("Server status:", data);
                if (data.status === "loading") {
                    const systemMessageContainer = document.createElement("div");
                    systemMessageContainer.className = "message-container bot-message";
                    const systemMessageContent = document.createElement("div");
                    systemMessageContent.className = "message-content";
                    systemMessageContent.innerHTML = `
                        <div class="message-role bot-role">System</div>
                        <div>Model is being loaded. This might take a minute...</div>
                    `;
                    systemMessageContainer.appendChild(systemMessageContent);
                    messages.appendChild(systemMessageContainer);
                    showNotification("Model Loading", "Please wait while the AI model is being initialized...");
                } else if (data.status === "ready" && data.model) {
                    showNotification("Ready", `Model ${data.model} is ready for chat`);
                }
                handleXarTitleVisibility();
            } else {
                console.error("Server not responding correctly");
                showNotification("Server Offline", "AI server appears to be offline. Please try again later.");
                handleXarTitleVisibility();
            }
        } catch (error) {
            console.error("Server connection failed:", error);
            showNotification("Server Offline", "AI server appears to be offline. Please try again later.");
            handleXarTitleVisibility();
        }
    }

    function createMessageElement(role, content, isTyping = false) {
        const fragment = document.createDocumentFragment();
        const messageContainer = document.createElement("div");
        messageContainer.className = `message-container ${role}-message`;
        const messageContent = document.createElement("div");
        messageContent.className = "message-content";
        const roleDiv = document.createElement("div");
        roleDiv.className = `message-role ${role}-role`;
        roleDiv.textContent = role === "user" ? "You" : "Assistant";
        messageContent.appendChild(roleDiv);
        if (isTyping) {
            const typingIndicator = document.createElement("div");
            typingIndicator.className = "typing-indicator";
            typingIndicator.innerHTML = "<span></span><span></span><span></span>";
            messageContent.appendChild(typingIndicator);
        } else {
            const contentDiv = document.createElement("div");
            contentDiv.textContent = content || "";
            messageContent.appendChild(contentDiv);
        }
        messageContainer.appendChild(messageContent);
        fragment.appendChild(messageContainer);
        return { fragment, messageContainer, messageContent };
    }

    let activeStreamConnection = null;
    let streamErrorCount = 0;

    sendBtn.addEventListener("click", async () => {
        const message = userInput.value.trim();
        if (!message) return;

        if (activeStreamConnection) {
            console.log("Aborting previous stream connection");
            activeStreamConnection.abort();
            activeStreamConnection = null;
        }

        userInput.value = "";
        userInput.style.height = 'auto';
        if (messages.childElementCount === 0) {
            xarTitleContainer.classList.add('minimized');
        }
        const { fragment: userFragment } = createMessageElement("user", message);
        messages.appendChild(userFragment);
        const { fragment: botFragment, messageContainer: botMessageContainer, 
                messageContent: botMessageContent } = createMessageElement("bot", "", true);
        messages.appendChild(botFragment);
        const responseElement = document.createElement("div");
        window.requestAnimationFrame(() => {
            messages.scrollTop = messages.scrollHeight;
        });
        userInput.disabled = true;
        sendBtn.disabled = true;
        try {
            const streamingSupported = typeof window.ReadableStream !== 'undefined';
            if (streamingSupported && streamErrorCount < OPTIMIZATION.maxStreamErrors) {
                const startTime = performance.now();

                activeStreamConnection = new AbortController();
                const timeoutId = setTimeout(() => {
                    console.log("Stream timeout triggered");
                    if (activeStreamConnection) {
                        activeStreamConnection.abort();
                    }
                }, OPTIMIZATION.streamTimeout);

                const response = await fetch("http://localhost:5000/chat", {
                    method: "POST",
                    headers: { 
                        "Content-Type": "application/json",
                        "Connection": "keep-alive"
                    },
                    body: JSON.stringify({ 
                        message,
                        stream: true,
                        max_tokens: OPTIMIZATION.maxResponseTokens
                    }),
                    signal: activeStreamConnection.signal
                });

                if (response.ok) {
                    botMessageContent.innerHTML = `<div class="message-role bot-role">Assistant</div>`;
                    botMessageContent.appendChild(responseElement);
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    let responseText = '';
                    let batchedChunks = '';
                    let updatesPending = 0;
                    let lastScrollTime = 0;
                    let chunkCount = 0;
                    const maxChunks = 5000;
                    const scrollThrottleTime = 150;

                    try {
                        while (true) {
                            const { value, done } = await reader.read();
                            if (done) break;

                            chunkCount++;
                            if (chunkCount > maxChunks) {
                                console.warn("Maximum chunk count exceeded, terminating stream");
                                break;
                            }

                            const chunk = decoder.decode(value, { stream: true });
                            const lines = chunk.split('\n\n');
                            let hasUpdate = false;

                            for (const line of lines) {
                                if (line.startsWith('data: ')) {
                                    try {
                                        const data = JSON.parse(line.slice(6));
                                        if (data.error) {
                                            responseElement.innerHTML = `<span class="error">Error: ${data.error}</span>`;
                                            break;
                                        } else if (data.done) {
                                            break;
                                        } else if (data.chunk) {
                                            // Improved chunk handling to prevent duplicates
                                            const newChunk = data.chunk.trim();
                                            
                                            // Skip empty chunks
                                            if (!newChunk) continue;
                                            
                                            // Simple duplicate prevention - don't add the same chunk twice in a row
                                            if (batchedChunks.endsWith(newChunk) || responseText.endsWith(newChunk)) {
                                                console.log("Skipping duplicate chunk:", newChunk);
                                                continue;
                                            }
                                            
                                            batchedChunks += newChunk;
                                            hasUpdate = true;
                                            updatesPending++;
                                        }
                                    } catch (e) {
                                        console.error('Error parsing SSE data', e);
                                        continue;
                                    }
                                }
                            }

                            const now = performance.now();
                            if ((hasUpdate && batchedChunks.length > OPTIMIZATION.chunkBufferThreshold) || 
                                (updatesPending > 10) || 
                                (now - lastScrollTime > scrollThrottleTime)) {
                                responseText += batchedChunks;
                                window.requestAnimationFrame(() => {
                                    // Clean up any potential duplicate phrases that might occur at chunk boundaries
                                    const cleanedText = responseText.replace(/(.{15,50})(\s+\1)/g, "$1");
                                    if (cleanedText !== responseText) {
                                        console.log("Cleaned up duplicate phrase in response");
                                        responseText = cleanedText;
                                    }
                                    
                                    responseElement.textContent = responseText;
                                    if (batchedChunks.length > OPTIMIZATION.chunkBufferThreshold) {
                                        messages.scrollTop = messages.scrollHeight;
                                        lastScrollTime = now;
                                    }
                                });
                                batchedChunks = '';
                                updatesPending = 0;
                            }
                        }
                        streamErrorCount = 0;
                    } catch (streamError) {
                        console.error("Stream reading error:", streamError);
                        streamErrorCount++;

                        if (responseText.length > 0) {
                            responseElement.textContent = responseText;
                        } else {
                            responseElement.innerHTML = 
                                `<span class="error">Error during streaming: ${streamError.message}</span>`;
                        }
                    } finally {
                        clearTimeout(timeoutId);
                    }
                } else {
                    const errorData = await response.json();
                    botMessageContent.innerHTML = `
                        <div class="message-role bot-role">Assistant</div>
                        <div><span class="error">Error: ${errorData.error || 'Unknown error'}</span></div>
                    `;
                }

                activeStreamConnection = null;
                clearTimeout(timeoutId);

            } else {
                const response = await fetch("http://localhost:5000/chat", {
                    method: "POST",
                    headers: { 
                        "Content-Type": "application/json",
                        "Connection": "keep-alive"
                    },
                    body: JSON.stringify({ 
                        message,
                        max_tokens: OPTIMIZATION.maxResponseTokens
                    }),
                });
                const data = await response.json();
                if (data.error) {
                    botMessageContent.innerHTML = `
                        <div class="message-role bot-role">Assistant</div>
                        <div><span class="error">Error: ${data.error}</span></div>
                    `;
                } else {
                    botMessageContent.innerHTML = `<div class="message-role bot-role">Assistant</div>`;
                    responseElement.textContent = data.response || "I don't have a response for that.";
                    botMessageContent.appendChild(responseElement);
                }
            }
        } catch (error) {
            console.error("Request error:", error);
            streamErrorCount++;

            botMessageContent.innerHTML = `
                <div class="message-role bot-role">Assistant</div>
                <div><span class="error">Network error. Please check your connection and try again.</span></div>
            `;

            if (activeStreamConnection) {
                activeStreamConnection = null;
            }

        } finally {
            userInput.disabled = false;
            sendBtn.disabled = false;
            userInput.focus();
            userInput.style.height = 'auto';
            window.requestAnimationFrame(() => {
                messages.scrollTop = messages.scrollHeight;
            });
        }
    });

    userInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendBtn.click();
        }
    });

    window.addEventListener('beforeunload', () => {
        if (activeStreamConnection) {
            activeStreamConnection.abort();
            activeStreamConnection = null;
        }
    });

    // Add chat history persistence
    const CHAT_HISTORY_KEY = 'xar_chat_history';
    let lastSaveTime = 0;
    const SAVE_INTERVAL = 5000; // Save at most every 5 seconds

    // Load chat history on startup
    function loadChatHistory() {
        try {
            const savedChat = localStorage.getItem(CHAT_HISTORY_KEY);
            if (savedChat) {
                const chatData = JSON.parse(savedChat);
                // Only restore if we have messages and they're not too old (24 hours max)
                if (chatData.messages && chatData.messages.length > 0 && 
                    (Date.now() - chatData.timestamp) < 24 * 60 * 60 * 1000) {
                    
                    // Reconstruct messages from saved data
                    chatData.messages.forEach(msg => {
                        const { fragment } = createMessageElement(msg.role, msg.content);
                        messages.appendChild(fragment);
                    });
                    
                    handleXarTitleVisibility();
                    window.requestAnimationFrame(() => {
                        messages.scrollTop = messages.scrollHeight;
                    });
                    
                    console.log("Restored chat history with", chatData.messages.length, "messages");
                }
            }
        } catch (e) {
            console.error("Error loading chat history:", e);
            // If there's a corruption, clear the history
            localStorage.removeItem(CHAT_HISTORY_KEY);
        }
    }

    // Save chat history but throttle to prevent excessive writes
    function saveChatHistory() {
        const now = Date.now();
        if (now - lastSaveTime < SAVE_INTERVAL) return;
        
        lastSaveTime = now;
        try {
            const chatMessages = [];
            document.querySelectorAll('.message-container').forEach(container => {
                const isUser = container.classList.contains('user-message');
                const role = isUser ? 'user' : 'bot';
                
                // Get the content (skip the role div)
                const contentDivs = container.querySelectorAll('.message-content > div:not(.message-role):not(.thoughts-toggle):not(.thoughts-container)');
                if (contentDivs.length > 0) {
                    let content = '';
                    contentDivs.forEach(div => {
                        content += div.textContent;
                    });
                    
                    chatMessages.push({ role, content });
                }
            });
            
            if (chatMessages.length > 0) {
                const chatData = {
                    timestamp: Date.now(),
                    messages: chatMessages
                };
                localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(chatData));
            }
        } catch (e) {
            console.error("Error saving chat history:", e);
        }
    }
    
    // Fix potential memory leaks with all running connections
    function cleanupConnections() {
        if (activeStreamConnection) {
            console.log("Cleaning up active stream connection");
            activeStreamConnection.abort();
            activeStreamConnection = null;
        }
        
        // Cleanup any speech recognition if active
        if (isRecording && recognition) {
            try {
                recognition.stop();
                isRecording = false;
            } catch (e) {
                console.error("Error stopping speech recognition:", e);
            }
        }
        
        if (silenceTimeout) {
            clearTimeout(silenceTimeout);
            silenceTimeout = null;
        }
    }

    // Create improved message element function that triggers history saving
    const originalCreateMessageElement = createMessageElement;
    createMessageElement = function(role, content, isTyping = false) {
        const result = originalCreateMessageElement(role, content, isTyping);
        // Only save history for real messages, not typing indicators
        if (!isTyping) {
            setTimeout(saveChatHistory, 100);
        }
        return result;
    };
    
    // Handle page visibility changes to prevent memory issues
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') {
            // Page is hidden, cleanup resources
            cleanupConnections();
            saveChatHistory();
        } else {
            // Page is visible again
            console.log("Page visible again");
        }
    });
    
    // Detect potential unintended refreshes
    let hasUnloaded = false;
    window.addEventListener('beforeunload', (event) => {
        if (!hasUnloaded) {
            cleanupConnections();
            saveChatHistory();
            hasUnloaded = true;
        }
    });

    // Modified send button handler to update chat history after sending
    const originalClickHandler = sendBtn.onclick;
    sendBtn.onclick = async function() {
        // Original handler logic
        if (originalClickHandler) {
            await originalClickHandler.apply(this, arguments);
        } else {
            // ...existing code...
        }
        
        // Save after each message
        setTimeout(saveChatHistory, 500);
    };
    
    // Add enhanced error recovery for streams
    async function handleStreamError(error, botMessageContent, responseElement, partialResponseText = '') {
        console.error("Stream error:", error);
        streamErrorCount++;
        
        // Try to recover with the partial response if possible
        if (partialResponseText) {
            responseElement.textContent = partialResponseText;
        } else {
            // Create a more helpful error message with recovery options
            botMessageContent.innerHTML = `
                <div class="message-role bot-role">Assistant</div>
                <div><span class="error">Connection error: ${error.message || 'Unknown error'}</span>
                <br><button class="retry-btn" onclick="retryLastMessage()">Retry</button></div>
            `;
        }
        
        // Add a retry function to the window object
        window.retryLastMessage = function() {
            // Implementation depends on your chat history structure
            // This is a placeholder
            console.log("Retry requested");
            // You'd implement actual retry logic here
        };
    }
    
    // Create a global function to reset all chat state
    window.resetChatState = function() {
        // Abort any active stream connection
        if (activeStreamConnection) {
            console.log("Aborting active stream connection during reset");
            activeStreamConnection.abort();
            activeStreamConnection = null;
        }
        
        // Reset any error counters
        streamErrorCount = 0;
        
        // Clear chat history from storage
        localStorage.removeItem(CHAT_HISTORY_KEY);
        
        // Reset XAR title container
        if (xarTitleContainer) {
            handleXarTitleVisibility();
        }
        
        // Reset any other state variables
        if (recognition && isRecording) {
            recognition.stop();
            isRecording = false;
            if (voiceBtn) {
                voiceBtn.classList.remove('recording');
                voiceBtn.innerHTML = '<i class="ri-mic-line"></i>';
                
                // Restore voice waves
                const voiceWave1 = document.createElement('div');
                const voiceWave2 = document.createElement('div');
                const voiceWave3 = document.createElement('div');
                voiceWave1.className = 'voice-wave';
                voiceWave2.className = 'voice-wave';
                voiceWave3.className = 'voice-wave';
                voiceBtn.appendChild(voiceWave1);
                voiceBtn.appendChild(voiceWave2);
                voiceBtn.appendChild(voiceWave3);
            }
        }
        
        // Clear any pending timeouts
        if (silenceTimeout) {
            clearTimeout(silenceTimeout);
            silenceTimeout = null;
        }
        
        console.log("Chat state has been completely reset");
    };
    
    // Call loadChatHistory on startup after DOM content is loaded
    setTimeout(loadChatHistory, 100);
    
    // Only check server status on first page load
    let statusChecked = sessionStorage.getItem('initialStatusChecked');
    if (!statusChecked) {
        checkServerStatus();
        sessionStorage.setItem('initialStatusChecked', 'true');
    }
    
    // Add automatic cleanup timer to prevent memory issues
    setInterval(() => {
        // Periodically check if we're running into memory issues
        const memoryUsage = performance.memory ? performance.memory.usedJSHeapSize : null;
        if (memoryUsage && memoryUsage > 100000000) { // Over ~100MB
            console.warn("High memory usage detected, performing cleanup");
            // Force garbage collection where possible
            if (window.gc) window.gc();
        }
    }, 60000); // Check every minute
});
