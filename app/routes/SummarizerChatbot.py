from flask import jsonify, request, Blueprint
from google import generativeai as genai
import os
import re

chatbot_bp = Blueprint('chatbot_bp', __name__)


@chatbot_bp.route('/start-questionaire', methods=['POST'])
def summarizer_chatbot():
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

    if(not request.is_json):
        return jsonify({
            {'error': 'Request must be in JSON format'}
        }), 400

    data = request.get_json()
    if(not data):
        return jsonify({'error': 'No JSON data received'}), 400

    # model = genai.GenerativeModel('gemini-2.0-flash')  # Use 'gemini-1.5-flash' or latest available
    model = genai.GenerativeModel('gemma-3-27b-it')  # Use 'gemini-1.5-flash' or latest available
    history = data.get("history")
    prompt = f"""
        You are a video-focused assistant that answers user questions **only in HTML format**, based on the video’s subject, content, and naturally related concepts.

        ###  HTML RESPONSE RULES
        1. Always respond with **pure HTML only** (no markdown, no explanations outside HTML).
        2. Use proper tags like <p>, <ul>, <li>, <strong>, <h2>, <h3> for clarity and structure.
        3. If showing code or structured data, wrap it in <pre><code>[...]</code></pre> and describe below with <p>.

        ---

        ### 易 SMART RELEVANCE RULES

        You must answer the question if it meets **any** of the following:

        - ✅ It is **directly covered** in the video.
        - ✅ It is **conceptually or categorically part** of the same subject (e.g., asking about other HTML tags in an HTML video, or other characters in a Fortnite game video).
        - ✅ It is **naturally relevant or commonly associated** with the video topic (e.g., Bitcoin in a Binance video, learning paths in a coding tutorial).
        - ✅ It is about the **tool/platform/ecosystem** shown in the video (e.g., "What is Udemy?" in a Udemy course video).
        - ✅ It is a **reasonable follow-up or extension**, such as:
        - "What else can I learn?"
        - "What are the next steps?"
        - "What are other features not mentioned?"

        Even if those things were not **explicitly discussed**, you should still answer them if they are logically connected to the video’s domain.

        ---

        You must **reject or ask for clarification** if the question:

        - ❌ Belongs to a **different domain or ecosystem** (e.g., PUBG in a Fortnite video, React in an HTML video).
        - ❌ Asks for **real-world unrelated data** (e.g., “Stock market rates today,” “ROI in my area”).
        - ❌ Is **unclear, vague, or contextless**.

        ---

        ###  VIDEO CONTEXT:
        \"\"\" 
        {history[0]['parts'][0]['text']} 
        \"\"\"

        ---

        ### ✅ GOOD QUESTIONS (Always Answer if Relevant to Video):
        - “What is Bitcoin?” → if video is about Binance or crypto
        - “What is the summary tag?” → if video is about HTML
        - “Is Storm King in Battle Royale too?” → if video is about Fortnite
        - “What other features are in this tool?” → if video is about a software product
        - “What tags weren’t mentioned in this video?” → if video is about HTML or a markup language
        - “What should I learn next?” → if video is educational

        ---

        ### ❌ BAD QUESTIONS (Always Reject):
        - “What is ROI in my area?” → real-world unrelated data
        - “What are stock rates today?” → off-topic economics
        - “Is this gun in PUBG?” → if video is about Fortnite
        - “What is React JS?” → if video is about plain HTML

        ---

        ### ❌ REJECTION RESPONSES (HTML ONLY)

        - **Off-topic**:  
        <p><em>This question doesn’t relate to the video’s topic or category. Try asking about something connected to the video.</em></p>

        - **Unclear**:  
        <p><em>I’m not sure what you mean. Could you rephrase your question or ask about a specific part of the video?</em></p>
    """

    history[0]['parts'][0]['text'] = prompt

    chat = model.start_chat(history=history)    
    query = history[-1]['parts'][0]['text']
    print(query)
    response = chat.send_message(query)
    
    return jsonify({
        'text':strip_code_markdowns(response.text)
    }), 200

def strip_code_markdowns(htmlText:str):
    return re.sub(r"```[\s\S]*?\n([\s\S]*?)```", r"\1", htmlText)
