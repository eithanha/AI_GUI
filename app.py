from flask import Flask, render_template, request, jsonify
import requests
import json
import os
from datetime import datetime

app = Flask(__name__)

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.1:8b"

# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, 'memory', 'chat_history.json')
MEMORY_FILE = os.path.join(BASE_DIR, 'memory', 'long_term_memory.md')

# Ensure memory directory exists
os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)

def load_long_term_memory():
    """Load markdown memory for AI context"""
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                return f.read()
        return "No long-term memory established yet."
    except Exception as e:
        print(f"Error loading memory: {e}")
        return ""

def load_chat_history():
    """Load recent chat history from JSON"""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('messages', [])
        return []
    except Exception as e:
        print(f"Error loading history: {e}")
        return []

def save_chat_history(messages):
    """Save chat history to JSON"""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "messages": messages,
                "last_updated": datetime.now().isoformat(),
                "total_messages": len(messages)
            }, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving history: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/history')
def get_history():
    """Return chat history"""
    messages = load_chat_history()
    return jsonify({"messages": messages})

@app.route('/api/memory')
def get_memory():
    """Return long-term memory (for viewing/editing)"""
    memory = load_long_term_memory()
    return jsonify({"memory": memory})

@app.route('/api/memory', methods=['POST'])
def update_memory():
    """Update long-term memory"""
    try:         
        data = request.json
        content = data.get('content', '')
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        messages = data.get('messages', [])
        
        # Load long-term memory
        long_term_memory = load_long_term_memory()
        
        # Build system prompt with memory
        system_prompt = f"""You are a helpful AI assistant with persistent memory.

## Long-term Memory
{long_term_memory}

## Instructions
- Use the long-term memory to provide personalized, contextual responses
- Remember details about the user's projects, preferences, and goals
- Be concise but helpful
- If the user mentions something that should be remembered long-term, 
  you can suggest adding it to their memory file
"""
        
        # Add system message at the beginning
        full_messages = [
            {"role": "system", "content": system_prompt}
        ] + messages
        
        # Save history
        save_chat_history(messages)
        
        # Call Ollama
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": full_messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 1000
                }
            },
            timeout=120
        )
        
        return jsonify(response.json())
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting AI Chat with Hybrid Memory System")
    print(f"📁 Chat history: {HISTORY_FILE}")
    print(f"🧠 Long-term memory: {MEMORY_FILE}")
    print("📍 Open http://localhost:5000")
    app.run(debug=True, port=5000)
