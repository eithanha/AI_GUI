const messagesDiv = document.getElementById("messages");
const chatContainer = document.getElementById("chat-container");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");

let conversationHistory = [];
let unreadCount = 0;

// Load saved conversations from localStorage
function loadHistory() {
  const saved = localStorage.getItem("chatHistory");
  if (saved) {
    conversationHistory = JSON.parse(saved);
    conversationHistory.forEach((msg) => {
      addMessageToUI(msg.role, msg.content, false);
    });
  }
}

// Save to localStorage
function saveHistory() {
  localStorage.setItem("chatHistory", JSON.stringify(conversationHistory));
}

// Check if user is at bottom of chat
function isUserAtBottom() {
  const threshold = 100;
  return (
    chatContainer.scrollHeight -
      chatContainer.scrollTop -
      chatContainer.clientHeight <
    threshold
  );
}

// Scroll to bottom
function scrollToBottom() {
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Add message to UI
// Add message to UI AND save to history
function addMessageToUI(role, content, save = true) {
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${role}`;
  messageDiv.textContent = content;
  messagesDiv.appendChild(messageDiv);

  // Auto-scroll
  setTimeout(() => {
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }, 50);

  // Save to history if requested
  if (save) {
    conversationHistory.push({ role, content });
    saveHistory();

    // Also sync to server
    syncHistoryToServer();
  }
}

// Sync history to server
async function syncHistoryToServer() {
  try {
    await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: conversationHistory,
        syncOnly: true, // Flag to indicate this is just syncing, not a new message
      }),
    });
  } catch (error) {
    console.log("Could not sync to server:", error);
  }
}

// Updated sendMessage function
async function sendMessage() {
  const text = messageInput.value.trim();
  if (!text) return;

  messageInput.disabled = true;
  sendButton.disabled = true;

  // Add user message (saves to history)
  addMessageToUI("user", text);
  messageInput.value = "";

  showTyping();

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: conversationHistory,
      }),
    });

    const data = await response.json();
    hideTyping();

    if (data.message) {
      // Add AI response (ALSO saves to history)
      addMessageToUI("assistant", data.message.content);
    } else if (data.error) {
      addMessageToUI("assistant", "Error: " + data.error);
    }
  } catch (error) {
    hideTyping();
    addMessageToUI("assistant", "❌ Failed to connect to AI");
    console.error(error);
  } finally {
    messageInput.disabled = false;
    sendButton.disabled = false;
    messageInput.focus();
  }
}

// Show unread messages indicator
function showUnreadIndicator() {
  let indicator = document.getElementById("unreadIndicator");
  if (!indicator) {
    indicator = document.createElement("div");
    indicator.id = "unreadIndicator";
    indicator.style.cssText = `
            position: fixed;
            bottom: 80px;
            left: 50%;
            transform: translateX(-50%);
            background: #19c37d;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
            z-index: 1000;
        `;
    indicator.onclick = () => {
      unreadCount = 0;
      chatContainer.scrollTop = chatContainer.scrollHeight;
      indicator.remove();
    };
    document.body.appendChild(indicator);
  }
  indicator.textContent = `${unreadCount} new message${unreadCount > 1 ? "s" : ""} ↓`;
  indicator.style.display = "block";
}

// Hide indicator when user scrolls to bottom
chatContainer.addEventListener("scroll", () => {
  if (isUserAtBottom() && unreadCount > 0) {
    unreadCount = 0;
    const indicator = document.getElementById("unreadIndicator");
    if (indicator) indicator.remove();
  }
});

// Show typing indicator
function showTyping() {
  const typingDiv = document.createElement("div");
  typingDiv.className = "message assistant typing";
  typingDiv.id = "typing-indicator";
  typingDiv.textContent = "AI is thinking";
  messagesDiv.appendChild(typingDiv);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function hideTyping() {
  const indicator = document.getElementById("typing-indicator");
  if (indicator) indicator.remove();
}

// Send message to backend
async function sendMessage() {
  const text = messageInput.value.trim();
  if (!text) return;

  messageInput.disabled = true;
  sendButton.disabled = true;

  addMessageToUI("user", text);
  messageInput.value = "";
  showTyping();
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: conversationHistory }),
    });

    const data = await response.json();
    hideTyping();

    if (data.message) {
      addMessageToUI("assistant", data.message.content);
    } else if (data.error) {
      addMessageToUI("assistant", "Error: " + data.error);
    }
  } catch (error) {
    hideTyping();
    addMessageToUI("assistant", "❌ Failed to connect to AI");
    console.error(error);
  } finally {
    messageInput.disabled = false;
    sendButton.disabled = false;
    messageInput.focus();
  }
}

// Event listeners
sendButton.addEventListener("click", sendMessage);
messageInput.addEventListener("keypress", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  loadHistory();
  messageInput.focus();

  // Load from server if available
  fetch("/api/history")
    .then((r) => r.json())
    .then((data) => {
      if (data.messages && data.messages.length > conversationHistory.length) {
        // Server has more recent history
        conversationHistory = data.messages;
        messagesDiv.innerHTML = "";
        data.messages.forEach((msg) => {
          addMessageToUI(msg.role, msg.content, false);
        });
        localStorage.setItem(
          "chatHistory",
          JSON.stringify(conversationHistory),
        );
      }
    })
    .catch(() => console.log("No server history available"));
});
