const messagesDiv = document.getElementById("messages");
const chatContainer = document.getElementById("chat-container");

const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
let userScrolledUp = false;
let shouldAutoScroll = true;

let conversationHistory = [];

console.log("=== SCRIPT LOADED ===");
console.log("messagesDiv:", document.getElementById("messages"));
console.log("chatContainer:", document.getElementById("chat-container"));

// Check if messages div exists
const el = document.getElementById("messages");
console.log("Element:", el);

// Check its properties
console.log("scrollHeight:", el.scrollHeight);
console.log("clientHeight:", el.clientHeight);
console.log("scrollTop:", el.scrollTop);

// Check CSS
console.log("overflow:", getComputedStyle(el).overflow);
console.log("overflowY:", getComputedStyle(el).overflowY);
console.log("height:", getComputedStyle(el).height);

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

// Add message to UI
function addMessageToUI(role, content, save = true) {
  // Check BEFORE adding message if user is at bottom
  const wasAtBottom =
    chatContainer.scrollHeight -
      chatContainer.scrollTop -
      chatContainer.clientHeight <
    150;

  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${role}`;
  messageDiv.textContent = content;
  messagesDiv.appendChild(messageDiv);

  // Only auto-scroll if user was at bottom BEFORE new message
  if (wasAtBottom) {
    setTimeout(() => {
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }, 10);
  }

  if (save) {
    conversationHistory.push({ role, content });
    saveHistory();
  }
}

// Force scroll after a delay to ensure render
setTimeout(() => {
  console.log("Attempting to scroll...");
  console.log("Setting scrollTop to:", chatContainer.scrollHeight);

  chatContainer.scrollTop = chatContainer.scrollHeight;

  console.log("After scroll - scrollTop:", chatContainer.scrollTop);

  // Check if it worked
  setTimeout(() => {
    console.log("100ms later - scrollTop:", chatContainer.scrollTop);
  }, 100);
}, 50);

// Scroll the CONTAINER, not the messages div
requestAnimationFrame(() => {
  const isNearBottom =
    chatContainer.scrollHeight -
      chatContainer.scrollTop -
      chatContainer.clientHeight <
    100;

  if (isNearBottom) {
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }
});

// Show typing indicator
function showTyping() {
  const typingDiv = document.createElement("div");
  typingDiv.className = "message assistant typing";
  typingDiv.id = "typing-indicator";
  typingDiv.textContent = "AI is thinking";
  messagesDiv.appendChild(typingDiv);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function hideTyping() {
  const indicator = document.getElementById("typing-indicator");
  if (indicator) indicator.remove();
}

// Send message to backend
async function sendMessage() {
  const text = messageInput.value.trim();
  if (!text) return;

  // Disable input while processing
  messageInput.disabled = true;
  sendButton.disabled = true;

  // Add user message
  addMessageToUI("user", text);
  messageInput.value = "";

  // Show typing indicator
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
    const aiMessage = data.message.content;

    hideTyping();
    addMessageToUI("assistant", aiMessage);
  } catch (error) {
    hideTyping();
    addMessageToUI(
      "assistant",
      "❌ Error: Could not connect to AI. Is Ollama running?",
    );
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

async function loadHistory() {
  try {
    const response = await fetch("/api/history");
    if (response.ok) {
      const data = await response.json();
      conversationHistory = data.messages || [];
      // Render saved messages...
    }
  } catch (error) {
    console.log("No history found, starting fresh");
    conversationHistory = [];
  }
}

// Load history when page loads
document.addEventListener("DOMContentLoaded", async function () {
  console.log("Loading chat history...");
  try {
    const response = await fetch("/api/history");
    const data = await response.json();

    if (data.messages && data.messages.length > 0) {
      console.log(`Loaded ${data.messages.length} messages`);
      conversationHistory = data.messages;

      // Render saved messages
      data.messages.forEach((msg) => {
        addMessageToUI(msg.role, msg.content, false); // false = don't save again
      });
    } else {
      console.log("No history found, starting fresh");
      conversationHistory = [];
    }
  } catch (error) {
    console.error("Failed to load history:", error);
    conversationHistory = [];
  }
});

// Detect if user is scrolling
messagesDiv.addEventListener("scroll", () => {
  const { scrollTop, scrollHeight, clientHeight } = messagesDiv;
  const isAtBottom = scrollHeight - scrollTop - clientHeight < 50; // 50px threshold

  shouldAutoScroll = isAtBottom;
  userScrolledUp = !isAtBottom;

  // Show/hide "scroll to bottom" button
  const scrollButton = document.getElementById("scrollToBottom");
  if (scrollButton) {
    scrollButton.style.display = userScrolledUp ? "block" : "none";
  }
});

// Smart scroll function
function scrollToBottom(smooth = true) {
  if (shouldAutoScroll) {
    messagesDiv.scrollTo({
      top: messagesDiv.scrollHeight,
      behavior: smooth ? "smooth" : "auto",
    });
  }
}

// Modified addMessageToUI function
function addMessageToUI(role, content, save = true) {
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${role}`;
  messageDiv.textContent = content;
  messagesDiv.appendChild(messageDiv);

  // Only auto-scroll if user is at bottom
  scrollToBottom();

  if (save) {
    conversationHistory.push({ role, content });
    saveHistory();
  }
}

// Add scroll-to-bottom button to your HTML
// Add this inside your <main> or <footer> in index.html:
/*
<button id="scrollToBottom" 
        style="display:none; position:fixed; bottom:80px; right:20px; 
               background:#19c37d; color:white; border:none; 
               border-radius:50%; width:40px; height:40px; 
               cursor:pointer; z-index:1000;">
    ↓
</button>
*/

// Add click handler for the button
document.addEventListener("DOMContentLoaded", function () {
  const scrollButton = document.getElementById("scrollToBottom");
  if (scrollButton) {
    scrollButton.addEventListener("click", () => {
      shouldAutoScroll = true;
      scrollToBottom();
      scrollButton.style.display = "none";
    });
  }
});

let unreadCount = 0;

function addMessageToUI(role, content, save = true) {
  const wasAtBottom = shouldAutoScroll;

  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${role}`;
  messageDiv.textContent = content;
  messagesDiv.appendChild(messageDiv);

  if (wasAtBottom) {
    // User was at bottom, auto-scroll
    scrollToBottom();
  } else {
    // User is reading history, show indicator
    unreadCount++;
    updateUnreadIndicator();
  }

  if (save) {
    conversationHistory.push({ role, content });
    saveHistory();
  }
}

function updateUnreadIndicator() {
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
      shouldAutoScroll = true;
      scrollToBottom();
      indicator.remove();
    };
    document.body.appendChild(indicator);
  }

  indicator.textContent = `${unreadCount} new message${unreadCount > 1 ? "s" : ""} ↓`;
  indicator.style.display = "block";
}

messagesDiv.addEventListener("scroll", () => {
  const { scrollTop, scrollHeight, clientHeight } = messagesDiv;
  if (scrollHeight - scrollTop - clientHeight < 50) {
    unreadCount = 0;
    const indicator = document.getElementById("unreadIndicator");
    if (indicator) indicator.remove();
  }
});
