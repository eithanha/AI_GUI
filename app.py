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
    """Execute a tool and return results"""
    action = tool_call.get('action')
    
    if action == 'web_search':
        query = tool_call.get('query', '')
        print(f"🔍 Web search: {query}")
        results = search_web(query)
        if not results:
            return "No web results found."
        
        # Format results
        formatted = f"Web search results for '{query}':\n\n"
        for i, r in enumerate(results, 1):
            formatted += f"{i}. {r['title']}\n   {r['snippet']}\n\n"
        return formatted
    
    elif action == 'get_weather':
        location = tool_call.get('location', 'Bangkok')
        # You could integrate a weather API here
        return f"Weather data for {location} would go here (integrate OpenWeather API)"
    
    return f"Unknown tool: {action}"

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
        
        # Save history
        save_chat_history(messages)
        
        # Load memory
        long_term_memory = load_long_term_memory()
        
        # Build system prompt with tools
        system_prompt = f"""You are a helpful AI assistant with access to tools and long-term memory.

## CRITICAL INSTRUCTION - READ CAREFULLY
When you need CURRENT or REAL-TIME information (weather, news, prices, scores, etc.), you MUST respond with EXACTLY this JSON format and NOTHING ELSE:

{{"action": "web_search", "query": "your search terms here"}}

DO NOT say "I don't have access" or "I can't browse the web". 
YOU HAVE ACCESS through the web_search tool. USE IT.

## Examples:

User: What's the weather in Bangkok?
You: {{"action": "web_search", "query": "Bangkok weather current"}}

User: Latest AI news
You: {{"action": "web_search", "query": "latest AI news today"}}

User: Tell me about Python (general knowledge - NO search needed)
You: Python is a programming language created by Guido van Rossum...

## Long-Term Memory
{long_term_memory}

## Tools Available:
1. web_search - Search the web for current information
   Format: {{"action": "web_search", "query": "search terms"}}
   
2. get_weather - Get weather data
   Format: {{"action": "get_weather", "location": "city name"}}

Remember: When you need current info, respond with ONLY the JSON. No extra text.
"""

        
        # Prepare messages
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        
        # Initial AI call
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": full_messages,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 500}
            },
            timeout=120
        )
        
        ai_response = response.json()
        ai_message = ai_response["message"]["content"]
        
        # Check if AI is requesting a tool
        tool_call = parse_tool_call(ai_message)
        
        if tool_call and "action" in tool_call:
            print(f"🛠️  AI requested tool: {tool_call}")
            
            # Execute the tool
            tool_result = execute_tool(tool_call)
            
            # Add tool result to conversation and get final answer
            tool_messages = full_messages + [
                {"role": "assistant", "content": ai_message},
                {"role": "user", "content": f"Tool result:\n{tool_result}\n\nNow provide a helpful answer to the original question using this information."}
            ]
            
            # Get final response with tool data
            final_response = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "messages": tool_messages,
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 800}
                },
                timeout=120
            )
            
            return jsonify(final_response.json())
        
        # No tool call, return direct response
        return jsonify(ai_response)
        
    except Exception as e:
        print(f"Chat error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 AI Chat with Tool Calling")
    print("=" * 60)
    print("📍 http://localhost:5000")
    print("🛠️  Tools: web_search, get_weather")
    print("=" * 60)
    app.run(debug=True, port=5000)
