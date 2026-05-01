from flask import Flask, render_template, request, jsonify
import requests
import json
import os
import re
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434/api/chat')
MODEL = os.getenv('MODEL', 'llama3.1:8b')
SERPAPI_KEY = os.getenv('SERPAPI_KEY')

# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, 'memory', 'chat_history.json')
MEMORY_FILE = os.path.join(BASE_DIR, 'memory', 'long_term_memory.md')

# Ensure memory directory exists
os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)


def load_long_term_memory():
    """Load long-term memory from markdown file"""
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                return f.read()
        return "No long-term memory established yet."
    except Exception as e:
        print(f"Error loading memory: {e}")
        return ""


def load_chat_history():
    """Load chat history from JSON file"""
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
    """Save chat history to JSON file"""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "messages": messages,
                "last_updated": datetime.now().isoformat(),
                "total_messages": len(messages)
            }, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving history: {e}")


def search_web(query, num_results=3):
    """Search web using SerpAPI"""
    if not SERPAPI_KEY:
        print("⚠️  SERPAPI_KEY not configured")
        return []
    
    try:
        from serpapi import GoogleSearch
        
        params = {
            "engine": "google",
            "q": query,
            "api_key": SERPAPI_KEY,
            "num": num_results
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        organic_results = results.get("organic_results", [])
        
        formatted_results = []
        for result in organic_results[:num_results]:
            formatted_results.append({
                'title': result.get('title', ''),
                'snippet': result.get('snippet', ''),
                'link': result.get('link', '')
            })
        
        return formatted_results
        
    except Exception as e:
        print(f"Web search error: {e}")
        return []


def needs_web_search(message):
    """Check if message requires web search"""
    keywords = [
        'weather', 'news', 'current', 'today', 'price', 'stock',
        'latest', 'who is', 'what is', 'when is', 'how much',
        'temperature', 'forecast', 'score', 'result'
    ]
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in keywords)


@app.route('/')
def index():
    """Serve main page"""
    return render_template('index.html')


@app.route('/api/history')
def get_history():
    """Get chat history"""
    messages = load_chat_history()
    return jsonify({"messages": messages})


@app.route('/api/chat', methods=['POST'])
def chat():
    """Main chat endpoint with web search integration"""
    try:
        data = request.json
        messages = data.get('messages', [])
        
        # Save chat history
        save_chat_history(messages)
        
        # Check if web search is needed
        web_context = ""
        if messages and messages[-1]['role'] == 'user':
            last_msg = messages[-1]['content']
            
            if needs_web_search(last_msg):
                print(f"\n🔍 Web search for: {last_msg[:60]}...")
                
                results = search_web(last_msg, num_results=3)
                
                if results:
                    web_context = "\n[REFERENCE: Current web search results]\n"
                    for i, r in enumerate(results, 1):
                        web_context += f"{i}. {r['title']}\n   {r['snippet']}\n\n"
                    web_context += "[End reference]\n\n"
                    print(f"✅ Found {len(results)} results")
                else:
                    web_context = "\n[No web results found]\n\n"
                    print("❌ No results")
        
        # Load long-term memory
        long_term_memory = load_long_term_memory()
        
        # Build system prompt
        system_prompt = f"""{web_context}

You are a helpful assistant with a friendly, casual tone.

PERSONALITY:
- Use emojis occasionally 😊
- Be concise (aim for under 3 sentences when possible)
- Be encouraging and positive
- Remember the user's name is Seng

CORE INSTRUCTIONS:
1. Read the web search results above as REFERENCE material
2. Extract the answer - DO NOT copy or repeat the reference text
3. DO NOT output "Source 1:", "Source 2:", or reference markers
4. Provide answers in natural, conversational English
5. For weather queries, include both °C and °F

EXAMPLES:
❌ BAD: "Source 1: Bangkok Weather - 97° 81°..."
✅ GOOD: "It's 97°F (36°C) in Bangkok today with thunderstorms expected."

FORMATTING:
- Use bullet points for lists
- Bold important terms with **text**
- Use markdown code blocks for code (with language tags)
- Include relevant links when mentioning websites
- Never use ALL CAPS

BEHAVIOR:
- If you don't know, say "I don't know" - don't guess
- Cite sources when using web results (e.g., "According to AccuWeather...")
- Explain technical topics simply first, then offer details
- Reference previous conversations when relevant

CONTENT:
- Keep responses family-friendly (no profanity)
- Avoid politics unless specifically asked
- Be patient and supportive if user seems frustrated
- Stay constructive and helpful

User's question: "{last_msg}"

Provide a helpful, natural response using the reference data above."""
        
        # Prepare messages for Ollama
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        
        # Call Ollama API
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
        
        if response.status_code != 200:
            return jsonify({"error": f"Ollama error: {response.text}"}), 500
        
        result = response.json()
        
        # Post-process: Convert JSON responses to text if needed
        ai_content = result.get("message", {}).get("content", "")
        if ai_content.strip().startswith('{'):
            try:
                data = json.loads(ai_content)
                # Extract text from JSON structure
                def extract_text(obj, texts=None):
                    if texts is None:
                        texts = []
                    if isinstance(obj, dict):
                        for v in obj.values():
                            extract_text(v, texts)
                    elif isinstance(obj, list):
                        for item in obj:
                            extract_text(item, texts)
                    elif isinstance(obj, str) and len(obj) > 3:
                        texts.append(obj)
                    return texts
                
                text_parts = extract_text(data)
                if text_parts:
                    ai_content = " ".join(text_parts[:5])
                    result["message"]["content"] = ai_content
            except:
                pass
        
        return jsonify(result)
        
    except requests.exceptions.Timeout:
        return jsonify({"error": "Request timed out. Is Ollama running?"}), 504
    except Exception as e:
        print(f"Chat error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/memory', methods=['GET', 'POST'])
def manage_memory():
    """Get or update long-term memory"""
    if request.method == 'GET':
        return jsonify({"memory": load_long_term_memory()})
    
    elif request.method == 'POST':
        try:
            data = request.json
            memory_content = data.get('memory', '')
            with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
                f.write(memory_content)
            
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Check if Ollama is accessible
        response = requests.get(
            OLLAMA_URL.replace('/api/chat', '/api/tags'),
            timeout=5
        )
        ollama_status = "connected" if response.status_code == 200 else "disconnected"
    except:
        ollama_status = "disconnected"
    
    return jsonify({
        "status": "healthy",
        "ollama": ollama_status,
        "model": MODEL,
        "serpapi_configured": bool(SERPAPI_KEY),
        "timestamp": datetime.now().isoformat()
    })


if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Local AI Chat Server")
    print("=" * 60)
    print(f"📍 URL: http://localhost:5000")
    print(f"🤖 Model: {MODEL}")
    print(f"🔍 Web Search: {'Enabled' if SERPAPI_KEY else 'Disabled (no API key)'}")
    print(f"💾 Memory: {MEMORY_FILE}")
    print("=" * 60)
    
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000,
        threaded=True
    )
