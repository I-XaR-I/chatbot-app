document.addEventListener("DOMContentLoaded", () => {
    const API_URL = "http://localhost:5000";
    const userInput = document.getElementById("userinput");
    const sendBtn = document.getElementById("sendbtn");
    const messages = document.getElementById("messages");

    // Check if server is running
    async function checkServerStatus() {
        try {
            const response = await fetch(`${API_URL}/status`, {
                method: "GET",
                headers: { "Content-Type": "application/json" }
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log("Server status:", data);
                
                if (data.status === "loading") {
                    // Show model loading message with ChatGPT-like styling
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
                } else if (data.status === "ready") {
                    // Show welcome message when model is ready
                    const welcomeMessageContainer = document.createElement("div");
                    welcomeMessageContainer.className = "message-container bot-message";
                    
                    const welcomeMessageContent = document.createElement("div");
                    welcomeMessageContent.className = "message-content";
                    
                    welcomeMessageContent.innerHTML = `
                        <div class="message-role bot-role">Assistant</div>
                        <div>Hello! How can I help you today?</div>
                    `;
                    
                    welcomeMessageContainer.appendChild(welcomeMessageContent);
                    messages.appendChild(welcomeMessageContainer);
                }
            } else {
                console.error("Server not responding correctly");
                
                // Show connection error message with ChatGPT-like styling
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
            }
        } catch (error) {
            console.error("Server connection failed:", error);
            
            // Show connection error message with ChatGPT-like styling
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
        }
    }

    // Run status check when page loads
    checkServerStatus();
});
