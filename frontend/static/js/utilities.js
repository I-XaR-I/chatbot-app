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

window.showNotification = showNotification;
