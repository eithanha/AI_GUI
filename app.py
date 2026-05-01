from flask import Flask, render_template, request, jsonify
import requests
import json
import os
import re
from datetime import datetime

app = Flask(__name__)

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.1:8b"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, 'memory', 'chat_history.json')
MEMORY_FILE = os.path.join(BASE_DIR, 'memory', 'long_term_memory.md')

os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)

# Tool definitions
TOOLS = {
    "web_search": {
        "description": "Search the web for current information",
        "parameters": {
            "query": "Search query string"
        }
    },
    "get_weather": {
        "description": "Get current weather for a location",
        "parameters": {
            "location": "City name"
        }
    }
}

def load_long_term_memory():
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                return f.read()
        return "No long-term memory established yet."
    except Exception as e:
        print(f"Error loading memory: {e}")
        return ""

def load_chat_history():
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
    """Search web using SerpAPI (you already have an API key!)"""
    try:
        from serpapi import GoogleSearch
        
        # Use your existing SerpAPI key
        API_KEY = "9046503278d3fad1f6b0aca10bbfa54b909f96f94a0c8003835831a46d53a72f"
        
        params = {
            "engine": "google",
            "q": query,
            "api_key": API_KEY,
            "num": num_results
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        # Extract organic results
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
        print(f"SerpAPI error: {e}")
        # Fallback to DuckDuckGo if SerpAPI fails
        return search_web_duckduckgo(query, num_results)

def search_web_duckduckgo(query, num_results=3):
    """Fallback DuckDuckGo search"""
    try:
        import requests
        from bs4 import BeautifulSoup
        
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        for result in soup.select('.result')[:num_results]:
            title_elem = result.select_one('.result__title')
            snippet_elem = result.select_one('.result__snippet')
            
            if title_elem and snippet_elem:
                results.append({
                    'title': title_elem.get_text(strip=True),
                    'snippet': snippet_elem.get_text(strip=True),
                    'link': ''
                })
        
        return results
    except Exception as e:
        print(f"DuckDuckGo error: {e}")
        return []


def parse_tool_call(text):
    """Extract JSON tool call from AI response - more lenient parsing"""
    text = text.strip()
    
    # Try direct JSON parse first
    try:
        data = json.loads(text)
        if isinstance(data, dict) and 'action' in data:
            return data
    except:
        pass
    
    # Try to find JSON in text (AI might add extra text)
    import re
    
    # Look for web_search pattern
    web_match = re.search(r'web_search.*?query["\']\s*:\s*["\']([^"\']+)["\']', text, re.IGNORECASE)
    if web_match:
        return {"action": "web_search", "query": web_match.group(1)}
    
    # Look for any JSON-like structure
    json_match = re.search(r'\{[^}]*"action"[^}]*\}', text, re.DOTALL)
    if json_match:
        try:
            # Clean up the JSON string
            json_str = json_match.group()
            # Fix common issues
            json_str = re.sub(r'(\w+):', r'"\1":', json_str)  # Add quotes to keys
            json_str = json_str.replace("'", '"')  # Fix single quotes
            return json.loads(json_str)
        except:
            pass
    
    # Check if AI is asking to search (even without proper JSON)
    if any(phrase in text.lower() for phrase in [
        "i need to search",
        "let me search",
        "i'll search for",
        "searching for"
    ]):
        # Extract what they're searching for
        # This is a fallback for when AI doesn't follow JSON format
        return {"action": "web_search", "query": text[:100]}
    
    return None


def execute_tool(tool_call):
    action = tool_call.get('action')
    print(f"🔧 Executing tool: {action}")
    print(f"   Parameters: {tool_call}")
    
    if action == 'web_search':
        query = tool_call.get('query', '')
        print(f"🔍 Searching for: {query}")
        
        results = search_web(query)
        print(f"📊 Got {len(results)} results")
        
        if results:
            for i, r in enumerate(results, 1):
                print(f"   {i}. {r['title'][:50]}...")
        else:
            print("   ❌ No results returned!")
        
        # ... rest of function


def get_weather_data(location):
    """Get actual weather data from OpenWeatherMap (free tier)"""
    try:
        # Get free API key from: https://openweathermap.org/api
        API_KEY = "a9976bdf9f381df5ed33b597d539b707"  # Free tier: 1000 calls/day
        
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": location,
            "appid": API_KEY,
            "units": "metric"
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if response.status_code == 200:
            return {
                "location": data["name"],
                "temp": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "humidity": data["main"]["humidity"],
                "description": data["weather"][0]["description"],
                "wind_speed": data["wind"]["speed"]
            }
        return None
    except Exception as e:
        print(f"Weather API error: {e}")
        return None

def execute_tool(tool_call):
    action = tool_call.get('action')
    
    if action == 'web_search':
        # ... existing code ...
        pass
    
    elif action == 'get_weather':
        location = tool_call.get('location', 'Bangkok')
        weather = get_weather_data(location)
        
        if weather:
            return f"""Current weather in {weather['location']}:
Temperature: {weather['temp']}°C (feels like {weather['feels_like']}°C)
Conditions: {weather['description']}
Humidity: {weather['humidity']}%
Wind: {weather['wind_speed']} m/s"""
        else:
            # Fallback to web search
            results = search_web(f"{location} weather")
            return format_search_results(results, f"{location} weather")


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/history')
def get_history():
    messages = load_chat_history()
    return jsonify({"messages": messages})

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        messages = data.get('messages', [])
        save_chat_history(messages)
        
        web_context = ""
        if messages and messages[-1]['role'] == 'user':
            last_msg = messages[-1]['content']
            print(f"\n{'='*60}")
            print(f"USER MESSAGE: {last_msg}")
            print(f"{'='*60}")
            
            # Check for search keywords
            if any(kw in last_msg.lower() for kw in ['weather', 'news', 'current', 'today', 'price', 'stock']):
                print("🔍 TRIGGERING WEB SEARCH...")
                
                try:
                    from serpapi import GoogleSearch
                    params = {
                        "engine": "google",
                        "q": last_msg,
                        "api_key": "9046503278d3fad1f6b0aca10bbfa54b909f96f94a0c8003835831a46d53a72f",
                        "num": 3
                    }
                    
                    print(f"   Query: {last_msg}")
                    search = GoogleSearch(params)
                    results = search.get_dict()
                    
                    print(f"   API Response keys: {results.keys()}")
                    
                    if 'organic_results' in results:
                        organic = results['organic_results']
                        print(f"   Found {len(organic)} results")
                        
                        # Build web context as REFERENCE MATERIAL (not copy-pasteable format)
                        web_context = "\n[REFERENCE: Current web search data for context]\n"
                        web_context += "Use this information to answer the user's question. Do NOT repeat this reference data.\n\n"
                        
                        for i, r in enumerate(organic[:3], 1):
                            title = r.get('title', '')
                            snippet = r.get('snippet', '')
                            # Make it look like notes, not something to output
                            web_context += f"Source {i}: {title} - {snippet}\n"
                        
                        web_context += "\n[End reference data]\n\n"
                        web_context += "Now answer the user's question using the reference data above. Respond in natural language.\n"

                    else:
                        print("   ❌ No 'organic_results' in response")
                        web_context = "\n\n[Web search returned no results]\n\n"
                        
                except Exception as e:
                    print(f"   ❌ SEARCH ERROR: {e}")
                    import traceback
                    traceback.print_exc()
                    web_context = f"\n\n[Web search failed: {e}]\n\n"
            else:
                print("ℹ️  No search keywords detected")
        
        # Build prompt with web context
        long_term_memory = load_long_term_memory()
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

Provide a helpful, natural response using the reference data above.
"""

        
        print(f"\n📝 System prompt length: {len(system_prompt)} chars")
        print(f"📝 Web context included: {len(web_context) > 0}")
        
        # Call Ollama
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": full_messages,
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 800}
            },
            timeout=120
        )
        
        result = response.json()
        ai_reply = result.get("message", {}).get("content", "")
        print(f"\n🤖 AI Response: {ai_reply[:150]}...")
        print(f"{'='*60}\n")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ CHAT ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/test-search')
def test_search():
    """Test the search function directly"""
    query = request.args.get('q', 'Bangkok weather')
    
    # Test both search methods
    print(f"Testing search for: {query}")
    
    # Try SerpAPI
    try:
        from serpapi import GoogleSearch
        params = {
            "engine": "google",
            "q": query,
            "api_key": "9046503278d3fad1f6b0aca10bbfa54b909f96f94a0c8003835831a46d53a72f",
            "num": 3
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        
        return jsonify({
            "method": "SerpAPI",
            "query": query,
            "success": True,
            "result_count": len(results.get("organic_results", [])),
            "results": results.get("organic_results", [])[:3]
        })
    except Exception as e:
        return jsonify({
            "method": "SerpAPI",
            "query": query,
            "success": False,
            "error": str(e)
        })


if __name__ == '__main__':
    print("=" * 60)
    print("🚀 AI Chat with Tool Calling")
    print("=" * 60)
    print("📍 http://localhost:5000")
    print("🛠️  Tools: web_search, get_weather")
    print("=" * 60)
    app.run(debug=True, port=5000)


