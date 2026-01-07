import os
import re
import time
from flask import Blueprint, request, jsonify
from google import generativeai as genai
from dotenv import load_dotenv
import argostranslate.translate
import argostranslate.package
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import requests

load_dotenv()
yvs_bp = Blueprint('yvs_bp', __name__)

# Debug: Check library version
try:
    import youtube_transcript_api
    print(f"DEBUG: youtube_transcript_api version: {getattr(youtube_transcript_api, '__version__', 'unknown')}")
    print(f"DEBUG: youtube_transcript_api file: {youtube_transcript_api.__file__}")
except Exception as e:
    print(f"DEBUG: Could not inspect youtube_transcript_api: {e}")

# Residential Proxy Configuration
PROXY_CONFIG = {
    "host": "p.webshare.io",
    "port": "80",
    "user": "cxjfcrft-1",
    "pass": "y4mi69ni1mxg"
}

def get_proxy_dict(proxy):
    """Convert proxy dict to requests proxy format with authentication"""
    if 'user' in proxy and 'pass' in proxy:
        proxy_url = f"http://{proxy['user']}:{proxy['pass']}@{proxy['host']}:{proxy['port']}"
    else:
        proxy_url = f"http://{proxy['ip']}:{proxy['port']}"
        
    return {
        "http": proxy_url,
        "https": proxy_url
    }

def fetch_with_proxy(url, timeout=10):
    """
    Fetch URL using the configured proxy.
    No fallback, no loop.
    """
    try:
        proxy_dict = get_proxy_dict(PROXY_CONFIG)
        print(f"Attempting fetch with proxy: {PROXY_CONFIG.get('host', PROXY_CONFIG.get('ip'))}:{PROXY_CONFIG['port']}")
        
        response = requests.get(url, proxies=proxy_dict, timeout=timeout)
        if response.status_code == 200:
            print(f"✓ Success with proxy")
            return response
        else:
            raise Exception(f"Request failed with status {response.status_code}")
            
    except Exception as e:
        print(f"✗ Proxy fetch failed: {e}")
        raise e

def get_transcript_with_proxy(video_id):
    """
    Fetch transcript using the configured proxy.
    Uses youtube-transcript-api v1.2.3+ style (http_client).
    No fallback, no loop.
    """
    try:
        proxy_dict = get_proxy_dict(PROXY_CONFIG)
        print(f"Attempting transcript fetch with proxy: {PROXY_CONFIG.get('host', PROXY_CONFIG.get('ip'))}:{PROXY_CONFIG['port']}")
        
        session = requests.Session()
        session.proxies.update(proxy_dict)
        
        # Instantiate API with the session (v1.2.3+ style)
        api = YouTubeTranscriptApi(http_client=session)
        
        # Use fetch method as verified
        if hasattr(api, 'fetch'):
            transcript = api.fetch(video_id)
            print(f"✓ Transcript success with proxy")
            return transcript
        else:
            # Fallback for safety, though debug confirmed 'fetch' exists
            if hasattr(api, 'get_transcript'):
                 return api.get_transcript(video_id)
            raise Exception("API instance has no 'fetch' or 'get_transcript' method")
            
    except Exception as e:
        print(f"✗ Transcript proxy fetch failed: {e}")
        raise e

def extract_video_id(url):
    """
    Extracts the video ID from various YouTube URL formats.
    """
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:shorts\/)([0-9A-Za-z_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
            
    return None

@yvs_bp.route('/get-transcription', methods=['POST'])
def get_transcription():
    start_time = time.time() 
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be in JSON format'}), 400

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400

        youtube_url = data.get('youtube_url')
        if not youtube_url:
            return jsonify({'error': 'YouTube URL is required'}), 400

        video_id = extract_video_id(youtube_url)
        if not video_id:
             return jsonify({'error': 'Invalid YouTube URL'}), 400

        transcription_text = ""
        video_title = "Unknown Title"
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        duration = 0
        embeded_url = f"https://www.youtube.com/embed/{video_id}"

        # --- LAYER 1: API (Captions) ---
        try:
            # Use the single proxy strategy
            transcript_data = get_transcript_with_proxy(video_id)

            if not transcript_data:
                raise Exception("No transcript data returned.")

            # Process Result (Handle dicts vs objects)
            text_parts = []
            for t in transcript_data:
                if isinstance(t, dict) and 'text' in t:
                    text_parts.append(t['text'])
                elif hasattr(t, 'text'):
                    text_parts.append(t.text)
                else:
                    text_parts.append(str(t))
            
            transcription_text = " ".join(text_parts)
            
            # Fetch metadata using requests + regex with proxy
            try:
                response = fetch_with_proxy(youtube_url, timeout=10)
                title_match = re.search(r'<meta property="og:title" content="(.*?)">', response.text)
                if title_match:
                    video_title = title_match.group(1)
            except Exception as e:
                print(f"Error fetching metadata: {e}")

        except (TranscriptsDisabled, NoTranscriptFound, Exception) as e:
            print(f"API Captions failed: {e}")
            return jsonify({'error': f'Failed to fetch captions: {str(e)}'}), 500

        total_time = round(time.time() - start_time, 2)
        return jsonify({
            'status': 'success',
            'videoTitle': video_title,
            'thumbnail': thumbnail_url,
            'transcription': transcription_text,
            'duration': duration,
            'embededUrl': embeded_url,
            'videoTime': total_time
        }), 200

    except Exception as e:
        print("TRANSCRIPTION ERROR : ", e)
        return jsonify({'error': str(e)}), 500

@yvs_bp.route('/get-youtube-video-summary', methods=['POST'])
def get_summary_of_the_video():
    if not request.is_json:
        return jsonify({'error': "Request must be in json format"}), 400
    
    data = request.get_json()
    prompt = f"""
        You are a highly intelligent assistant that creates long-form HTML summaries of videos or articles.
        📌 Your goal:
        Summarize the provided content into 2–3 times its original length, emphasizing clarity, structure, depth, and insight—as if preparing a detailed article or comprehensive report. Enhance the summary by elaborating on implications, providing additional context, and including practical examples relevant to the content.
        ✅ Summary Format Guidelines:
        Start with:
        - <p><strong>In this video...</strong></p>
        - Structure the summary with clear sections, using:
            - <h2> for main topics.
            - <h3> for subtopics.
            - <p> for descriptive paragraphs, detailed explanations, and contextual elaboration.
            - <ul> and <li> to list points, highlights, key takeaways, or examples clearly.
            - Use <strong> to bold key terms, concepts, important names, or phrases crucial for understanding.
        If the original content relates to coding or programming concepts:
            - Include practical code examples relevant to the content, formatted neatly within <pre><code> blocks.
            - After each code snippet, provide a detailed explanation in <p> tags to clarify what the code does, how it works, or its significance to the broader topic.
        Ensure the summary genuinely reflects the tone, structure, and intent of the original content. If the original content is short or brief, thoughtfully expand upon its ideas by adding related context, deeper insights, examples, or possible implications to achieve the desired length.
        ❌ Do NOT:
            - Include <html>, <body>, <script>, or <style> tags.
            - Provide generic filler content, repetitions, or unrelated commentary.
            - Introduce new topics or headings that are not grounded in or directly related to the original content.
        📄 Content to summarize:
        \"\"\"
        {data['content']}
        \"\"\"
    """

    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    model = genai.GenerativeModel("gemini-2.0-flash")
    summarization = model.generate_content(prompt).text
    cleanedSummarization = strip_summary_markdowns(summarization)

    return jsonify({
        "summary": cleanedSummarization        
    }), 200


def strip_summary_markdowns(changed_code: str):
    return re.sub(r"```[\s\S]*?\n([\s\S]*?)```", r"\1", changed_code)


@yvs_bp.route('/languages', methods=["GET"])
def get_all_languages():
    try:
        installed_languages = argostranslate.package.get_installed_packages()

        languages = [
            {
                "from_code": pkg.from_code,
                "from_name": pkg.from_name,
                "to_code": pkg.to_code,
                "to_name": pkg.to_name
            }
            for pkg in installed_languages
        ]
        
        return jsonify({"languages": languages}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@yvs_bp.route('/translate', methods=["POST"])
def translate_text():
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be in JSON format'}), 400

        data = request.get_json()
        print(data)
        text = data.get('q')
        target_code = data.get('target')

        if not text or not target_code:
            return jsonify({'error': 'Both "q" (text) and "target" (language code) are required'}), 400

        available_translations = argostranslate.translate.get_installed_languages()

        from_lang = argostranslate.translate.get_language_from_code('en') 
        to_lang = next((lang for lang in available_translations if lang.code == target_code), None)

        print("TO_LANG : ", to_lang)
        print("FROM_LANG : ", from_lang)

        if not to_lang:
            return jsonify({'error': f'Language code "{target_code}" not installed'}), 400

        translation = from_lang.get_translation(to_lang)
        translated_text = translation.translate(text)

        return jsonify({
            "translated": translated_text
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500