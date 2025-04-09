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
    
    const toggleSidebar = (show) => {
        if (show) {
            sidebar.style.display = "flex";
            sidebar.style.transform = "translateX(-100%)";
            
            sidebar.offsetHeight;
            
            sidebar.style.transform = "translateX(0)";
            sidebar.classList.remove("hidden");
        } else {
            sidebar.style.transform = "translateX(-100%)";
            chatarea.style.marginLeft = "0";
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
            inputArea.style.width = "90%";
        } else {
            openSidebarBtn.style.display = "none";
            inputArea.style.width = "85%";
        }
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
    
    const savedDarkMode = localStorage.getItem("darkMode");
    if (savedDarkMode === "enabled") {
        setDarkMode(true);
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
    
    window.addEventListener("resize", adjustLayout);
    
    if (window.innerWidth < 768) {
        toggleSidebar(false);
    } else {
        toggleSidebar(true);
    }
    
    sendBtn.addEventListener("click", () => {
        const message = userInput.value.trim();
        if (message) {
            userInput.value = "";
            userInput.focus();
        }
    });
    
    userInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            sendBtn.click();
        }
    });
});
