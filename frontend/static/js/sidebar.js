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
    const darkModeToggle = document.getElementById("darkModeToggle");
    // Replace fastModeToggle with new button
    const fastModeBtn = document.getElementById("fastModeBtn");
    
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
            // Center content by removing sidebar margin
            chatarea.classList.remove("with-sidebar");
        } else {
            openSidebarBtn.style.display = "none";
            // Adjust for sidebar presence
            chatarea.classList.add("with-sidebar");
        }
        
        // Force recalculation of messages container width
        setTimeout(() => {
            // Trigger re-layout
            messages.style.display = "none";
            messages.offsetHeight; // Force reflow
            messages.style.display = "flex";
        }, 310); // Just after transition completes
    };
    
    const startNewChat = () => {
        messages.innerHTML = '';
        userInput.focus();
    };
    
    function setDarkMode(isDark) {
        if (isDark) {
            document.body.classList.add("dark-mode");
            if (darkModeToggle) darkModeToggle.checked = true;
            
            sidebar.style.transition = "background-color 0.3s ease, transform 0.3s ease";
        } else {
            document.body.classList.remove("dark-mode");
            if (darkModeToggle) darkModeToggle.checked = false;
            
            sidebar.style.transition = "background-color 0.3s ease, transform 0.3s ease";
        }
        
        localStorage.setItem("darkMode", isDark ? "enabled" : "disabled");
    }
    
    function setFastMode(isFast) {
        if (isFast) {
            // Update for button instead of checkbox
            if (fastModeBtn) {
                fastModeBtn.classList.add("active");
            }
            document.body.classList.add("fast-mode");
            // Notification removed, relying on visual glow effect
        } else {
            // Update for button instead of checkbox
            if (fastModeBtn) {
                fastModeBtn.classList.remove("active");
            }
            document.body.classList.remove("fast-mode");
        }
        
        localStorage.setItem("fastMode", isFast ? "enabled" : "disabled");
    }
    
    // Function to show notification
    function showNotification(title, message) {
        const notification = document.createElement("div");
        notification.className = "notification";
        notification.innerHTML = `
            <div class="notification-title">${title}</div>
            <div class="notification-message">${message}</div>
        `;
        document.body.appendChild(notification);
        
        // Auto-hide after 3 seconds
        setTimeout(() => {
            notification.classList.add("hide");
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
    
    // Toggle thoughts visibility
    function toggleThoughts(element) {
        const thoughtsContainer = element.nextElementSibling;
        element.classList.toggle('open');
        thoughtsContainer.classList.toggle('open');
    }
    
    // Attach event listener for thoughts toggle - using event delegation
    document.addEventListener('click', (e) => {
        if (e.target.closest('.thoughts-toggle')) {
            toggleThoughts(e.target.closest('.thoughts-toggle'));
        }
    });
    
    const savedDarkMode = localStorage.getItem("darkMode");
    if (savedDarkMode === "enabled") {
        setDarkMode(true);
    }
    
    const savedFastMode = localStorage.getItem("fastMode");
    if (savedFastMode === "enabled") {
        setFastMode(true);
    }
    
    openSidebarBtn.addEventListener("click", () => toggleSidebar(true));
    closeSidebarBtn.addEventListener("click", () => toggleSidebar(false));
    
    if (newChatBtn) {
        newChatBtn.addEventListener("click", startNewChat);
    }
    
    if (darkModeToggle) {
        darkModeToggle.addEventListener("change", () => {
            setDarkMode(darkModeToggle.checked);
        });
    }
    
    // Update fast mode toggle event listener for button
    if (fastModeBtn) {
        fastModeBtn.addEventListener("click", () => {
            const currentState = fastModeBtn.classList.contains("active");
            setFastMode(!currentState);
        });
    }
    
    window.addEventListener("resize", () => {
        adjustLayout();
        
        // Automatically hide sidebar on mobile
        if (window.innerWidth < 768 && !sidebar.classList.contains("hidden")) {
            toggleSidebar(false);
        }
    });
    
    if (window.innerWidth < 768) {
        toggleSidebar(false);
    } else {
        toggleSidebar(true);
    }
    
    // Auto-resize textarea as user types
    userInput.addEventListener('input', function() {
        this.style.height = 'auto';
        const newHeight = Math.min(this.scrollHeight, 200);
        this.style.height = newHeight + 'px';
    });
    
    sendBtn.addEventListener("click", async () => {
        const message = userInput.value.trim();
        if (message) {
            // Display user message with updated styling
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
    
            // Clear input and disable while processing
            userInput.value = "";
            userInput.disabled = true;
            sendBtn.disabled = true;
            
            // Add a bot message container with updated styling
            const botMessageContainer = document.createElement("div");
            botMessageContainer.className = "message-container bot-message";
            
            const botMessageContent = document.createElement("div");
            botMessageContent.className = "message-content";
            
            // Start with the typing indicator
            botMessageContent.innerHTML = `
                <div class="message-role bot-role">Assistant</div>
                <div class="typing-indicator"><span></span><span></span><span></span></div>
            `;
            
            botMessageContainer.appendChild(botMessageContent);
            messages.appendChild(botMessageContainer);
            
            // Auto-scroll to bottom
            messages.scrollTop = messages.scrollHeight;
    
            try {
                // Determine if browser supports EventSource for streaming
                const streamingSupported = typeof EventSource !== 'undefined';
                
                if (streamingSupported) {
                    // Use streaming API with thoughts parameter
                    const response = await fetch("http://localhost:5000/chat", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ 
                            message, 
                            stream: true,
                            fast: document.body.classList.contains("fast-mode"),
                            include_thoughts: true
                        }),
                    });
                    
                    if (response.ok) {
                        // Set up SSE connection
                        const reader = response.body.getReader();
                        const decoder = new TextDecoder();
                        let responseText = '';
                        let thoughtsText = '';
                        
                        // Remove typing indicator
                        botMessageContent.innerHTML = `<div class="message-role bot-role">Assistant</div>`;
                        let responseElement = document.createElement("div");
                        botMessageContent.appendChild(responseElement);
                        
                        // Process the stream
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
                                            // Streaming complete - add thoughts if available
                                            console.log(`Response completed in ${data.processing_time}`);
                                            
                                            if (data.thoughts || thoughtsText) {
                                                thoughtsText = data.thoughts || thoughtsText;
                                                
                                                // Add the thoughts box
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
                                            // Append new text
                                            responseText += data.chunk;
                                            responseElement.innerText = responseText;
                                            
                                            // Auto-scroll to keep up with streaming text
                                            messages.scrollTop = messages.scrollHeight;
                                        } else if (data.thought_chunk) {
                                            // Collect thought chunks separately
                                            thoughtsText += data.thought_chunk;
                                        }
                                    } catch (e) {
                                        console.error('Error parsing SSE data', e);
                                    }
                                }
                            }
                        }
                    } else {
                        // Handle HTTP error
                        const errorData = await response.json();
                        botMessageContent.innerHTML = `
                            <div class="message-role bot-role">Assistant</div>
                            <div><span class="error">Error: ${errorData.error || 'Unknown error'}</span></div>
                        `;
                    }
                } else {
                    // Fall back to regular API
                    const response = await fetch("http://localhost:5000/chat", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ 
                            message,
                            fast: document.body.classList.contains("fast-mode"),
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
                        responseElement.textContent = data.response || "I don't have a response for that.";
                        botMessageContent.appendChild(responseElement);
                        
                        // Add thoughts if available
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
                // Re-enable input
                userInput.disabled = false;
                sendBtn.disabled = false;
                userInput.focus();
                
                // Reset textarea height
                userInput.style.height = 'auto';
                
                // Auto-scroll to bottom
                messages.scrollTop = messages.scrollHeight;
            }
        }
    });
    
    userInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            sendBtn.click();
        }
    });
});
