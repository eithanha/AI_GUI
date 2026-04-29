const messagesDiv = document.getElementById("messages");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");

let conversationHistory = [];

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
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${role}`;
  messageDiv.textContent = content;
  messagesDiv.appendChild(messageDiv);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;

  if (save) {
    conversationHistory.push({ role, content });
    saveHistory();
  }
}

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

// Load history on page load
loadHistory();
messageInput.focus();
