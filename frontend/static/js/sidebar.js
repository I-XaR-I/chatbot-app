document.addEventListener("DOMContentLoaded", () => {
    const sidebar = document.getElementById("sidebar");
    const openSidebarBtn = document.getElementById("opensidebarbtn");
    const closeSidebarBtn = document.getElementById("closesidebarbtn");
    const chatarea = document.getElementById("chatarea");
    const inputArea = document.getElementById("inputarea");
    const userInput = document.getElementById("userinput");
    const sendBtn = document.getElementById("sendbtn");
    const messages = document.getElementById("messages");
    const sidebarWidth = 260;
    const newChatBtn = document.getElementById("newchatbtn");
    const settingsDarkMode = document.getElementById("settingsDarkMode");
    const fontSizeSlider = document.getElementById("fontSizeSlider");
    const fontSizeValue = document.getElementById("fontSizeValue");
    const eyeComfortMode = document.getElementById("eyeComfortMode");
    const eyeComfortIntensity = document.getElementById("eyeComfortIntensity");
    const eyeComfortValue = document.getElementById("eyeComfortValue");

    const toggleSidebar = (show) => {
        if (show) {
            sidebar.style.display = "flex";
            sidebar.style.transform = "translateX(-100%)";
            sidebar.offsetHeight;
            sidebar.style.transform = "translateX(0)";
            sidebar.classList.remove("hidden");
            chatarea.classList.add("with-sidebar");
        } else {
            sidebar.style.transform = "translateX(-100%)";
            chatarea.classList.remove("with-sidebar");
            sidebar.classList.add("hidden");
            setTimeout(() => {
                if (sidebar.classList.contains("hidden")) {
                    sidebar.style.display = "none";
                    sidebar.style.transform = "";
                }
            }, 300);
        }
        adjustLayout();
    };

    const adjustLayout = () => {
        const sidebarHidden = sidebar.classList.contains("hidden");
        if (sidebarHidden) {
            openSidebarBtn.style.display = "flex";
            chatarea.classList.remove("with-sidebar");
        } else {
            openSidebarBtn.style.display = "none";
            chatarea.classList.add("with-sidebar");
        }
        setTimeout(() => {
            messages.style.display = "none";
            messages.offsetHeight;
            messages.style.display = "flex";
        }, 310);
    };

    const startNewChat = () => {
        messages.innerHTML = '';
        userInput.focus();
    };

    function setDarkMode(isDark) {
        setTimeout(() => {
            if (isDark) {
                document.body.classList.add("dark-mode");
                if (settingsDarkMode) settingsDarkMode.checked = true;
            } else {
                document.body.classList.remove("dark-mode");
                if (settingsDarkMode) settingsDarkMode.checked = false;
            }
            localStorage.setItem("darkMode", isDark ? "enabled" : "disabled");
            if (fontSizeSlider && fontSizeValue) {
                setFontSize(fontSizeSlider.value);
            }
        }, 5);
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

    function toggleThoughts(element) {
        const thoughtsContainer = element.nextElementSibling;
        element.classList.toggle('open');
        thoughtsContainer.classList.toggle('open');
    }

    document.addEventListener('click', (e) => {
        if (e.target.closest('.thoughts-toggle')) {
            toggleThoughts(e.target.closest('.thoughts-toggle'));
        }
    });

    function setFontSize(size) {
        document.documentElement.style.setProperty('--message-font-size', `${size}px`);
        if (fontSizeValue) {
            fontSizeValue.textContent = `${size}px`;
        }
        if (fontSizeSlider) {
            const min = fontSizeSlider.min || 14;
            const max = fontSizeSlider.max || 20;
            const percentage = ((size - min) / (max - min)) * 100;
            fontSizeSlider.style.background = `linear-gradient(to right, var(--primary-color) 0%, var(--primary-color) ${percentage}%, 
                                              ${document.body.classList.contains('dark-mode') ? 'var(--border-dark)' : 'var(--border-light)'} ${percentage}%, 
                                              ${document.body.classList.contains('dark-mode') ? 'var(--border-dark)' : 'var(--border-light)'} 100%)`;
        }
        localStorage.setItem('fontSize', size);
    }

    function setEyeComfortMode(enabled, intensity = 1) {
        document.body.classList.remove('eye-comfort-level-1', 'eye-comfort-level-3');
        document.body.classList.toggle('eye-comfort-active', enabled);
        if (enabled) {
            let overlay = document.querySelector('.eye-comfort-overlay');
            if (!overlay) {
                overlay = document.createElement('div');
                overlay.className = 'eye-comfort-overlay';
                document.body.appendChild(overlay);
            }
            document.body.classList.add(`eye-comfort-level-${intensity}`);
            if (eyeComfortIntensity) {
                eyeComfortIntensity.value = intensity;
            }
            localStorage.setItem("eyeComfortMode", "enabled");
            localStorage.setItem("eyeComfortIntensity", intensity);
        } else {
            const overlay = document.querySelector('.eye-comfort-overlay');
            if (overlay) {
                overlay.remove();
            }
            localStorage.setItem("eyeComfortMode", "disabled");
        }
    }

    const savedFontSize = localStorage.getItem('fontSize') || 16;
    if (fontSizeSlider) {
        fontSizeSlider.value = savedFontSize;
        setFontSize(savedFontSize);
        fontSizeSlider.addEventListener('input', () => {
            setFontSize(fontSizeSlider.value);
        });
    }

    const savedEyeComfortMode = localStorage.getItem("eyeComfortMode");
    const savedEyeComfortIntensity = parseInt(localStorage.getItem("eyeComfortIntensity") || "1");
    if (savedEyeComfortMode === "enabled" && eyeComfortMode) {
        eyeComfortMode.checked = true;
        if (eyeComfortIntensity) {
            eyeComfortIntensity.value = savedEyeComfortIntensity === 3 ? "3" : "1";
        }
        setEyeComfortMode(true, savedEyeComfortIntensity);
    }

    if (eyeComfortMode) {
        eyeComfortMode.addEventListener("change", () => {
            const intensity = eyeComfortIntensity ? parseInt(eyeComfortIntensity.value) : 2;
            setEyeComfortMode(eyeComfortMode.checked, intensity);
        });
    }

    if (eyeComfortIntensity) {
        eyeComfortIntensity.addEventListener("change", () => {
            if (eyeComfortMode && eyeComfortMode.checked) {
                setEyeComfortMode(true, parseInt(eyeComfortIntensity.value));
            }
        });
    }

    const savedDarkMode = localStorage.getItem("darkMode");
    if (savedDarkMode === "enabled") {
        setDarkMode(true);
    }

    openSidebarBtn.addEventListener("click", () => toggleSidebar(true));
    closeSidebarBtn.addEventListener("click", () => toggleSidebar(false));
    if (newChatBtn) {
        newChatBtn.addEventListener("click", startNewChat);
    }

    window.addEventListener("resize", () => {
        adjustLayout();
        if (window.innerWidth < 768 && !sidebar.classList.contains("hidden")) {
            toggleSidebar(false);
        }
    });

    if (window.innerWidth < 768) {
        toggleSidebar(false);
    } else {
        toggleSidebar(true);
    }

    userInput.addEventListener('input', function() {
        this.style.height = 'auto';
        const newHeight = Math.min(this.scrollHeight, 200);
        this.style.height = newHeight + 'px';
    });

    sendBtn.addEventListener("click", async () => {
        const message = userInput.value.trim();
        if (message) {
            const userMessageContainer = document.createElement("div");
            userMessageContainer.className = "message-container user-message";
            const userMessageContent = document.createElement("div");
            userMessageContent.className = "message-content";
            userMessageContent.innerHTML = `
                <div class="message-role user-role">You</div>
                <div>${message}</div>
            `;
            userMessageContainer.appendChild(userMessageContent);
            messages.appendChild(userMessageContainer);
            userInput.value = "";
            userInput.disabled = true;
            sendBtn.disabled = true;
            const botMessageContainer = document.createElement("div");
            botMessageContainer.className = "message-container bot-message";
            const botMessageContent = document.createElement("div");
            botMessageContent.className = "message-content";
            botMessageContent.innerHTML = `
                <div class="message-role bot-role">Assistant</div>
                <div class="typing-indicator"><span></span><span></span><span></span></div>
            `;
            botMessageContainer.appendChild(botMessageContent);
            messages.appendChild(botMessageContainer);
            messages.scrollTop = messages.scrollHeight;
            try {
                const streamingSupported = typeof EventSource !== 'undefined';
                if (streamingSupported) {
                    const response = await fetch("http://localhost:5000/chat", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ 
                            message, 
                            stream: true,
                            include_thoughts: true
                        }),
                    });
                    if (response.ok) {
                        const reader = response.body.getReader();
                        const decoder = new TextDecoder();
                        let responseText = '';
                        let thoughtsText = '';
                        botMessageContent.innerHTML = `<div class="message-role bot-role">Assistant</div>`;
                        let responseElement = document.createElement("div");
                        botMessageContent.appendChild(responseElement);
                        while (true) {
                            const { value, done } = await reader.read();
                            if (done) break;
                            const chunk = decoder.decode(value, { stream: true });
                            const lines = chunk.split('\n\n');
                            for (const line of lines) {
                                if (line.startsWith('data: ')) {
                                    try {
                                        const data = JSON.parse(line.slice(6));
                                        if (data.error) {
                                            responseElement.innerHTML = `<span class="error">Error: ${data.error}</span>`;
                                            break;
                                        } else if (data.done) {
                                            if (data.thoughts || thoughtsText) {
                                                thoughtsText = data.thoughts || thoughtsText;
                                                const thoughtsToggle = document.createElement("div");
                                                thoughtsToggle.className = "thoughts-toggle";
                                                thoughtsToggle.innerHTML = `<i class="ri-arrow-down-s-line"></i>Show thoughts`;
                                                const thoughtsContainer = document.createElement("div");
                                                thoughtsContainer.className = "thoughts-container";
                                                const thoughtsContent = document.createElement("div");
                                                thoughtsContent.className = "thoughts-content";
                                                thoughtsContent.innerText = thoughtsText;
                                                thoughtsContainer.appendChild(thoughtsContent);
                                                botMessageContent.appendChild(thoughtsToggle);
                                                botMessageContent.appendChild(thoughtsContainer);
                                            }
                                            break;
                                        } else if (data.chunk) {
                                            responseText += data.chunk;
                                            responseElement.innerHTML = marked.parse(responseText);
                                            messages.scrollTop = messages.scrollHeight;
                                        } else if (data.thought_chunk) {
                                            thoughtsText += data.thought_chunk;
                                        }
                                    } catch (e) {
                                        console.error('Error parsing SSE data', e);
                                    }
                                }
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
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ 
                            message,
                            include_thoughts: true
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
                        const responseElement = document.createElement("div");
                        responseElement.innerHTML = marked.parse(data.response || "I don't have a response for that.");
                        botMessageContent.appendChild(responseElement);
                        if (data.thoughts) {
                            const thoughtsToggle = document.createElement("div");
                            thoughtsToggle.className = "thoughts-toggle";
                            thoughtsToggle.innerHTML = `<i class="ri-arrow-down-s-line"></i>Show thoughts`;
                            const thoughtsContainer = document.createElement("div");
                            thoughtsContainer.className = "thoughts-container";
                            const thoughtsContent = document.createElement("div");
                            thoughtsContent.className = "thoughts-content";
                            thoughtsContent.innerText = data.thoughts;
                            thoughtsContainer.appendChild(thoughtsContent);
                            botMessageContent.appendChild(thoughtsToggle);
                            botMessageContent.appendChild(thoughtsContainer);
                        }
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
                messages.scrollTop = messages.scrollHeight;
            }
        }
    });

    userInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            sendBtn.click();
        }
    });

    const settingsBtn = document.getElementById("settingsbtn");
    const settingsModal = document.getElementById("settingsModal");
    const closeSettingsBtn = document.getElementById("closeSettingsBtn");
    const settingsTabs = document.querySelectorAll(".settings-sidebar li");
    const settingsContent = document.querySelectorAll(".settings-tab");

    function openSettingsModal() {
        setTimeout(() => {
            settingsModal.classList.add("active");
            if (settingsDarkMode) {
                settingsDarkMode.checked = document.body.classList.contains("dark-mode");
            }
        }, 10);
    }

    function closeSettingsModal() {
        settingsModal.classList.remove("active");
    }

    function switchSettingsTab(tabId) {
        settingsTabs.forEach(tab => {
            if (tab.dataset.tab === tabId) {
                tab.classList.add("active");
            } else {
                tab.classList.remove("active");
            }
        });
        settingsContent.forEach(content => {
            if (content.id === tabId) {
                content.classList.add("active");
            } else {
                content.classList.remove("active");
            }
        });
    }

    if (settingsBtn) {
        settingsBtn.addEventListener("click", openSettingsModal);
    }

    if (closeSettingsBtn) {
        closeSettingsBtn.addEventListener("click", closeSettingsModal);
    }

    if (settingsModal) {
        settingsModal.addEventListener("click", (e) => {
            if (e.target === settingsModal || e.target.classList.contains("settings-backdrop")) {
                closeSettingsModal();
            }
        });
    }

    settingsTabs.forEach(tab => {
        tab.addEventListener("click", () => {
            const tabId = tab.dataset.tab;
            switchSettingsTab(tabId);
        });
    });

    if (settingsDarkMode) {
        settingsDarkMode.addEventListener("change", () => {
            setDarkMode(settingsDarkMode.checked);
        });
    }
});
