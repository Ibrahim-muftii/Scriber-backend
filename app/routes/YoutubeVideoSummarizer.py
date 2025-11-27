import os
import argostranslate.translate
from app.utils.video_downloader import download_video
import re
from flask import Blueprint, request, jsonify, after_this_request
from google import generativeai as genai
from dotenv import load_dotenv
import time
from argostranslate.translate import get_installed_languages
import argostranslate
from faster_whisper import WhisperModel as ws
import traceback

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



def download_youtube_audio(url, output_path='videos'):
    """
    Downloads YouTube video using Playwright and SaveFrom.net.
    Returns: (audio_path, video_title, thumbnail_url, embedded_url, duration)
    """
    print("Downloading via Playwright...")
    try:
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        file_path, title, thumbnail, embed, duration = download_video(url, output_path)
        
        if file_path and os.path.exists(file_path):
            return file_path, title, thumbnail, embed, duration
        else:
            print("[FAILURE] Download failed or file not found.")
            return None, None, None, None, None

    except Exception as e:
        print("An error occurred while downloading or processing the video:")
        traceback.print_exc()
        return None, None, None, None, None


# def transcribe_video(audio_path):
#     """Transcribe audio using CPU-only faster-whisper"""
#     print("Starting CPU-based transcription...")
    
#     try:
#         # Force CPU usage with int8 for better performance
#         model = ws(
#             "small",
#             device="cpu",
#             compute_type="int8",
#             cpu_threads=os.cpu_count() or 4
#         )
        
#         result, _ = model.transcribe(
#             audio_path, 
#             beam_size=1,
#             vad_filter=False,
#             language="en"
#         )
        
#         full_text = " ".join(segment.text for segment in result)
#         print("[SUCCESS] Transcription completed")
#         return full_text
        
#     except Exception as e:
#         print(f"[ERROR] Transcription failed: {str(e)}")
#         raise Exception(f"Failed to transcribe audio: {str(e)}")

# def transcribe_video(audio_path):
#     model = ws("tiny", device='cpu',compute_type="float32", cpu_threads=4)
#     result,_ = model.transcribe(audio_path,beam_size=1,vad_filter=True,language='en')
#     full_text = " ".join(word.text for word in result)
#     return full_text

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