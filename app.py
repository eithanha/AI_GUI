from flask import Flask, render_template, request, jsonify
import requests
import os

app = Flask(__name__,
            static_folder='static',
            template_folder='templates')

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
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
