from flask import Flask, render_template, request, jsonify
import requests
import json
import os

# Configuration
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.1:8b"
HISTORY_FILE = 'chat_history.json'

# Create Flask app FIRST
app = Flask(__name__)

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/history')
def get_history():
    """Load chat history from file"""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        return jsonify({"messages": []})
    except Exception as e:
        return jsonify({"messages": [], "error": str(e)})

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        data = request.json
        messages = data.get('messages', [])
        
        # Save history to file
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump({"messages": messages}, f, indent=2)
        
        # Call Ollama API
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.7
                }
            },
            timeout=120
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                "error": f"Ollama returned status {response.status_code}"
            }), 500
            
    except requests.exceptions.ConnectionError:
        return jsonify({
            "message": {
                "content": "❌ Cannot connect to Ollama. Make sure it's running: ollama serve"
            }
        }), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Flask server...")
    print("📍 Open http://localhost:5000 in your browser")
    print("💡 Make sure Ollama is running: ollama serve")
    app.run(debug=True, port=5000, host='0.0.0.0')
