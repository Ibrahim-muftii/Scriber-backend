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

# List of proxies (first 10 from your list)
PROXY_LIST = [
    {"ip": "144.125.164.158", "port": "8080"},
    {"ip": "139.99.237.62", "port": "80"},
    {"ip": "72.10.160.90", "port": "1237"},
    {"ip": "20.242.243.105", "port": "3128"},
    {"ip": "213.142.156.97", "port": "80"},
    {"ip": "38.54.71.67", "port": "80"},
    {"ip": "219.93.101.63", "port": "80"},
    {"ip": "139.59.1.14", "port": "80"},
    {"ip": "34.216.224.9", "port": "40715"},
    {"ip": "219.93.101.62", "port": "80"}
]

def get_proxy_dict(proxy):
    """Convert proxy dict to requests proxy format"""
    proxy_url = f"http://{proxy['ip']}:{proxy['port']}"
    return {
        "http": proxy_url,
        "https": proxy_url
    }

def fetch_with_proxy_fallback(url, timeout=10):
    """
    Try to fetch URL with proxy fallback.
    First tries without proxy, then tries each proxy in the list.
    """
    # Try without proxy first
    try:
        print(f"Attempting to fetch without proxy...")
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            print(f"✓ Success without proxy")
            return response
    except Exception as e:
        print(f"✗ Direct connection failed: {e}")
    
    # Try with each proxy
    for idx, proxy in enumerate(PROXY_LIST, 1):
        try:
            proxy_dict = get_proxy_dict(proxy)
            print(f"Attempting proxy {idx}/{len(PROXY_LIST)}: {proxy['ip']}:{proxy['port']}")
            
            response = requests.get(url, proxies=proxy_dict, timeout=timeout)
            if response.status_code == 200:
                print(f"✓ Success with proxy {proxy['ip']}:{proxy['port']}")
                return response
        except Exception as e:
            print(f"✗ Proxy {proxy['ip']}:{proxy['port']} failed: {e}")
            continue
    
    # All proxies failed
    raise Exception("All proxies failed to fetch the URL")

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
            transcript_data = None
            
            # Strategy 1: list_transcripts (Modern - v0.4.0+)
            if hasattr(YouTubeTranscriptApi, 'list_transcripts'):
                try:
                    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                    try:
                        transcript = transcript_list.find_manually_created_transcript(['en'])
                    except:
                        try:
                            transcript = transcript_list.find_generated_transcript(['en'])
                        except:
                            transcript = next(iter(transcript_list))
                    transcript_data = transcript.fetch()
                except Exception as e:
                    print(f"Strategy 1 failed: {e}")

            # Strategy 2: get_transcript (Standard Static - v0.2.0+)
            if not transcript_data and hasattr(YouTubeTranscriptApi, 'get_transcript'):
                try:
                    transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
                except Exception as e:
                    print(f"Strategy 2 failed: {e}")

            # Strategy 3: Instance fetch (Legacy/Alternative)
            if not transcript_data:
                try:
                    api = YouTubeTranscriptApi()
                    if hasattr(api, 'fetch'):
                        transcript_data = api.fetch(video_id)
                except Exception as e:
                    print(f"Strategy 3 failed: {e}")

            if not transcript_data:
                raise Exception("No compatible transcription method found or all failed.")

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
            
            # Fetch metadata using requests + regex with proxy fallback
            try:
                response = fetch_with_proxy_fallback(youtube_url, timeout=10)
                title_match = re.search(r'<meta property="og:title" content="(.*?)">', response.text)
                if title_match:
                    video_title = title_match.group(1)
            except Exception as e:
                print(f"Error fetching metadata with all proxies: {e}")

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