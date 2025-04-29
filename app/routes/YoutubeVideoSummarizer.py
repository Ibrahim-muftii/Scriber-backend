import os
import yt_dlp
import re
from flask import Blueprint, request, jsonify,after_this_request
from google import generativeai as genai
from dotenv import load_dotenv
from faster_whisper import WhisperModel as ws

load_dotenv()
yvs_bp = Blueprint('yvs_bp', __name__)



@yvs_bp.route('/get-transcription', methods=['POST'])
def get_transcription():
    """Handles the API request to transcribe a YouTube video."""
    try:

        if not request.is_json:
            return jsonify({'error': 'Request must be in JSON format'}), 400

        data = request.get_json()

        if not data:
            return jsonify({'error': 'No JSON data received'}), 400

        youtube_url = data.get('youtube_url')
        if not youtube_url:
            return jsonify({'error': 'YouTube URL is required'}), 400

        audio_path, video_title, thumbnail_url, embeded_url, duration = download_youtube_video(youtube_url)

        if duration > 900:
            return jsonify({'error': 'Can not process video of duration more than 15 minutes'}), 400 

        if not audio_path:
            return jsonify({'error': 'Failed to download video'}), 500
        transcription_text = trancribe_video(audio_path)

        @after_this_request
        def cleanUp(response):
            try:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            except Exception as cleanup_error:
                print(f"Error deleting audio file: {cleanup_error}")
            return response

        return jsonify({
            'status': 'success',
            'videoTitle':video_title,
            'thumbnail':thumbnail_url,
            'transcription': transcription_text,
            'duration':duration,
            'embededUrl':embeded_url
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def download_youtube_video(url, output_path='videos'):

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_path, 'audio.%(ext)s'),
        'noplaylist': True,
        'cookiefile': 'cookies.txt',
        'verbose': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            audio_path = os.path.join(output_path, 'audio.mp3')
            video_title = info.get('title', 'Unknown Title')
            thumbnail_url = info.get('thumbnail', '')
            duration = info.get('duration')
            embeded_url = f"https://www.youtube.com/embed/{info['id']}"
            return audio_path, video_title, thumbnail_url, embeded_url, duration
    except Exception as e:
        print(f"Error downloading audio: {e}")
        return None, None, None, None

def trancribe_video(audio_path):
    model = ws("tiny", device='cpu',compute_type="float32", cpu_threads=4)
    result,_ = model.transcribe(audio_path,beam_size=1,vad_filter=True)
    full_text = " ".join(word.text for word in result)
    return full_text

@yvs_bp.route('/get-youtube-video-summary', methods=['POST'])
def get_summary_of_the_video():
    if(not request.is_json):
        return jsonify({'error', "Request must be in json format"}),400
    
    data = request.get_json()
    prompt = f"""
        You are a highly intelligent assistant that creates **long-form HTML summaries** of videos or articles.

        📌 Your goal:
        Summarize the given content into **2–3x its original length**, with a focus on clarity, structure, and depth — as if preparing an article or report.

        ✅ Summary Format Guidelines:
        - Start with: <p><strong>In this video...</strong></p>
        - Structure the summary with meaningful sections using <h2> and <h3> for key topics and subtopics.
        - Use <p> for detailed paragraphs under each section.
        - Use <ul> and <li> to capture bullet points where appropriate (for lists, highlights, takeaways, etc.)
        - Use <strong> to **bold** key terms, concepts, or important names.
        - Reflect the **tone and structure** of the content faithfully.
        - If the original content is short, **expand** it by elaborating on implications, examples, or context based on what's presented.
        - The output should be 2–3 times the original content's length.
        - Avoid repetition, filler, or generic text.

        ❌ Do NOT:
        - Include <html>, <body>, <script>, or <style> tags.
        - Add any commentary or meta-explanation.
        - Use headings or text that are not grounded in the original content.

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
        "summary":cleanedSummarization        
    }), 200

def strip_summary_markdowns(changed_code:str):
    return re.sub(r"```[\s\S]*?\n([\s\S]*?)```", r"\1", changed_code)