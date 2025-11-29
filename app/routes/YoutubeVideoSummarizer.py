import os
import yt_dlp
import subprocess
import argostranslate.translate

import re
from flask import Blueprint, request, jsonify, after_this_request
from google import generativeai as genai
from dotenv import load_dotenv
import time
from argostranslate.translate import get_installed_languages
import argostranslate
from faster_whisper import WhisperModel as ws
import traceback
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

load_dotenv()
yvs_bp = Blueprint('yvs_bp', __name__)


@yvs_bp.route('/get-transcription', methods=['POST'])
def get_transcription():
    print("STARTED..... ")
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

        audio_path, video_title, thumbnail_url, embeded_url, duration = download_youtube_audio(youtube_url)

        if duration > 900:
            return jsonify({'error': 'Can not process video of duration more than 15 minutes'}), 400 

        if not audio_path:
            return jsonify({'error': 'Failed to download video'}), 500
            
        transcription_text = transcribe_video(audio_path)

        @after_this_request
        def cleanUp(response):
            try:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            except Exception as cleanup_error:
                print(f"Error deleting audio file: {cleanup_error}")
            return response
        
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


def get_youtube_cookies(url):
    """
    Launches a headless browser to visit the YouTube URL and extract cookies.
    This helps bypass bot detection by providing valid session cookies.
    """
    print("Getting cookies via Playwright...")
    cookies = []
    user_agent = ""
    try:
        with sync_playwright() as p:
            # Launch headless browser
            browser = p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # Apply stealth
            stealth_sync(page)
            
            # Navigate to the video
            print(f"Navigating to {url}...")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Wait a bit for cookies to be set
            time.sleep(5)
            
            # Handle Consent Popup (if any)
            try:
                # Common selectors for "Accept all" or "Reject all"
                consent_button = page.query_selector('button[aria-label="Accept all"], button[aria-label="Reject all"], #onetrust-accept-btn-handler')
                if consent_button:
                    print("Clicking consent button...")
                    consent_button.click()
                    time.sleep(2)
            except Exception as e:
                print(f"Consent handling ignored: {e}")

            # Get cookies and UA
            cookies = context.cookies()
            user_agent = page.evaluate("navigator.userAgent")
            print(f"Extracted {len(cookies)} cookies. UA: {user_agent}")
            browser.close()
            
            return cookies, user_agent
            
    except Exception as e:
        print(f"Failed to get cookies: {e}")
        return [], ""

def download_youtube_audio(url, output_path='videos'):
    print("Downloading...")
    try:
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        # 1. Get dynamic cookies and UA
        cookies, user_agent = get_youtube_cookies(url)
        
        # Create a temporary cookies file
        temp_cookie_file = os.path.join(output_path, f"temp_cookies_{int(time.time())}.txt")
        if cookies:
            with open(temp_cookie_file, 'w') as f:
                f.write("# Netscape HTTP Cookie File\n")
                for cookie in cookies:
                    # Convert Playwright cookie to Netscape format
                    domain = cookie['domain']
                    flag = "TRUE" if domain.startswith('.') else "FALSE"
                    path = cookie['path']
                    secure = "TRUE" if cookie['secure'] else "FALSE"
                    expiration = str(int(cookie['expires'])) if 'expires' in cookie else "0"
                    name = cookie['name']
                    value = cookie['value']
                    f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}\n")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_path, 'audio.%(ext)s'),
            'noplaylist': True,
            'verbose': False,
            'quiet': True,
            'no_warnings': True,
            # Use Android client as primary stealth
            'extractor_args': {'youtube': {'player_client': ['android']}},
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        }

        # Use the temp cookie file if we got cookies
        if cookies and os.path.exists(temp_cookie_file):
            print(f"Using dynamic cookies from {temp_cookie_file}")
            ydl_opts['cookiefile'] = temp_cookie_file
        
        # Sync User Agent if available
        if user_agent:
            print(f"Syncing User Agent: {user_agent}")
            ydl_opts['user_agent'] = user_agent

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                audio_path = os.path.join(output_path, 'audio.mp3')
                video_title = info.get('title', 'Unknown Title')
                thumbnail_url = info.get('thumbnail', '')
                duration = info.get('duration', 0)
                embedded_url = f"https://www.youtube.com/embed/{info['id']}"
                
                return audio_path, video_title, thumbnail_url, embedded_url, duration
        finally:
            # Clean up temp cookie file
            if os.path.exists(temp_cookie_file):
                try:
                    os.remove(temp_cookie_file)
                    print(f"Deleted temp cookie file: {temp_cookie_file}")
                except Exception as e:
                    print(f"Error deleting temp cookie file: {e}")

    except Exception as e:
        print("An error occurred while downloading or processing the video:")
        traceback.print_exc()
        return None, None, None, None, None

def transcribe_video(audio_path, final_output_path="videos/audio.wav.txt"):
    print("transcribing the video")
    model_path = "whisper.cpp/models/ggml-base.en.bin"
    whisper_cli = "whisper.cpp/build/bin/whisper-cli"

    command = [
        whisper_cli,
        "-m", model_path,
        "-f", audio_path,
        "--threads", "4",
        "--language", "en",
        "--output-txt"
    ]

    try:     
        subprocess.run(command, check=True)
        
        with open(final_output_path, "r", encoding="utf-8") as f:
            result = f.read().strip()
        os.remove(final_output_path)

        return result

    except Exception as e:
        print(f"Transcription failed: {e}")
        return ""


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