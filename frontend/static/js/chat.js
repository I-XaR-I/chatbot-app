document.addEventListener("DOMContentLoaded", () => {
    const API_URL = "http://localhost:5000";
    const userInput = document.getElementById("userinput");
    const sendBtn = document.getElementById("sendbtn");
    const voiceBtn = document.getElementById("voiceBtn");
    const messages = document.getElementById("messages");
    const xarTitleContainer = document.getElementById("xar-title-container");

    const OPTIMIZATION = {
        useStreaming: true,
        maxResponseTokens: 512,
        streamChunkSize: 10,
        chunkBufferThreshold: 25
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
                const errorMessageContainer = document.createElement("div");
                errorMessageContainer.className = "message-container bot-message";
                const errorMessageContent = document.createElement("div");
                errorMessageContent.className = "message-content";
                errorMessageContent.innerHTML = `
                    <div class="message-role bot-role">System</div>
                    <div class="error">Cannot connect to the AI server. Please make sure the server is running.</div>
                `;
                errorMessageContainer.appendChild(errorMessageContent);
                messages.appendChild(errorMessageContainer);
                handleXarTitleVisibility();
            }
        } catch (error) {
            console.error("Server connection failed:", error);
            const errorMessageContainer = document.createElement("div");
            errorMessageContainer.className = "message-container bot-message";
            const errorMessageContent = document.createElement("div");
            errorMessageContent.className = "message-content";
            errorMessageContent.innerHTML = `
                <div class="message-role bot-role">System</div>
                <div class="error">Cannot connect to the AI server. Please make sure the server is running.</div>
            `;
            errorMessageContainer.appendChild(errorMessageContent);
            messages.appendChild(errorMessageContainer);
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

    sendBtn.addEventListener("click", async () => {
        const message = userInput.value.trim();
        if (!message) return;
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
            if (streamingSupported) {
                const startTime = performance.now();
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
                    const scrollThrottleTime = 150;
                    while (true) {
                        const { value, done } = await reader.read();
                        if (done) break;
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
                                        batchedChunks += data.chunk;
                                        hasUpdate = true;
                                        updatesPending++;
                                    }
                                } catch (e) {
                                    console.error('Error parsing SSE data', e);
                                }
                            }
                        }
                        const now = performance.now();
                        if ((hasUpdate && batchedChunks.length > OPTIMIZATION.chunkBufferThreshold) || 
                            (updatesPending > 10) || 
                            (now - lastScrollTime > scrollThrottleTime)) {
                            responseText += batchedChunks;
                            window.requestAnimationFrame(() => {
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
                } else {
                    const errorData = await response.json();
                    botMessageContent.innerHTML = `
                        <div class="message-role bot-role">Assistant</div>
                        <div><span class="error">Error: ${errorData.error || 'Unknown error'}</span></div>
                    `;
                }
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
            botMessageContent.innerHTML = `
                <div class="message-role bot-role">Assistant</div>
                <div><span class="error">Network error. Please check your connection and try again.</span></div>
            `;
            console.error("Error:", error);
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

    checkServerStatus();
});
