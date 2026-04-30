from flask import Flask, render_template, request, jsonify
import requests
import json
import os

app = Flask(__name__)

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.1:8b"

# Use absolute path for history file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, 'chat_history.json')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/history', methods=['GET'])
def get_history():
    """Load chat history"""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"Loaded {len(data.get('messages', []))} messages from history")
                return jsonify(data)
        return jsonify({"messages": []})
    except Exception as e:
        print(f"Error loading history: {e}")
        return jsonify({"messages": []})

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        messages = data.get('messages', [])
        
        # Save history immediately
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump({"messages": messages}, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(messages)} messages to history")
        
        # Call Ollama
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": messages,
                "stream": False
            },
            timeout=120
        )
        
        return jsonify(response.json())
        
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print(f"History file location: {HISTORY_FILE}")
    app.run(debug=True, port=5000)
