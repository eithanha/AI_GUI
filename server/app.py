from flask import Flask, render_template, request, jsonify
import requests
import os

app = Flask(__name__)

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.1:8b"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        messages = data.get('messages', [])
        
        # Call Ollama
        
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 500
                }
            },
            timeout=120
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
          
        else:
            return jsonify({"error": f"Ollama error: {response.status_code}"}), 500
            
    except requests.exceptions.ConnectionError:
        return jsonify({
            "message": {
                "content": "❌ Cannot connect to Ollama. Make sure it's running with: ollama serve"
            }
        }), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting AI Chat Interface...")
    print("📍 Open http://localhost:5000 in your browser")
    print("💡 Make sure Ollama is running: ollama serve")
    app.run(debug=True, port=5000)
