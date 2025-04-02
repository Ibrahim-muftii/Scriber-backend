from flask import Blueprint, request, jsonify
import os
import time
import requests
import yt_dlp
import subprocess
from dotenv import load_dotenv


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

        video_path, video_title, thumbnail_url, embeded_url = download_youtube_video(youtube_url)
        if not video_path:
            return jsonify({'error': 'Failed to download video'}), 500


        audio_file = extract_audio_with_ffmpeg(video_path)
        if not audio_file:
            return jsonify({'error': 'Failed to extract audio'}), 500


        upload_url = upload_audio(os.getenv('ASSEMBLY_AI_API_KEY'), audio_file)
        if not upload_url:
            return jsonify({'error': 'Failed to upload audio'}), 500


        transcript_id = request_transcription(os.getenv('ASSEMBLY_AI_API_KEY'), upload_url)
        if not transcript_id:
            return jsonify({'error': 'Failed to request transcription'}), 500


        transcription_text = poll_transcription(os.getenv('ASSEMBLY_AI_API_KEY'), transcript_id, audio_file)


        return jsonify({
            'status': 'success',
            'videoTitle':video_title,
            'thumbnail':thumbnail_url,
            'transcription': transcription_text,
            'embededUrl':embeded_url
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def download_youtube_video(url, output_path='videos'):

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    ydl_opts = {
        'format': 'worstvideo+bestaudio/best',
        'outtmpl': os.path.join(output_path, 'video.%(ext)s'),
        'noplaylist': True,
        'verbose': True,
        'merge_output_format': 'mp4',
        'cookiefile': 'cookies.txt',
        'postprocessor_args': ['-strict', '-2']
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_title = info.get('title', 'Unknown Title')
            thumbnail_url = info.get('thumbnail', '')
            video_path = os.path.join(output_path, "video.mp4")
            embeded_url = f"https://www.youtube.com/embed/{info['id']}"
            return video_path, video_title, thumbnail_url, embeded_url
    except Exception as e:
        return None


def extract_audio_with_ffmpeg(video_path, audio_path='videos/audio', bitrate='64k'):

    if not os.path.exists(audio_path):
        os.makedirs(audio_path)

    audio_file = os.path.join(audio_path, 'compressed_audio.mp3')
    cmd = [
        'ffmpeg', '-i', video_path, '-vn',
        '-acodec', 'libmp3lame', '-b:a', bitrate, '-y', audio_file
    ]

    try:
        subprocess.run(cmd, check=True)

        if os.path.exists(video_path):
            os.remove(video_path)

        return audio_file
    except subprocess.CalledProcessError as e:
        return None

def upload_audio(api_key, audio_file_path):

    headers = {'authorization': api_key}
    with open(audio_file_path, 'rb') as audio_file:
        response = requests.post('https://api.assemblyai.com/v2/upload', headers=headers, data=audio_file)

        if response.status_code == 200:
            return response.json().get('upload_url')
        else:
            return None


def request_transcription(api_key, audio_url):

    headers = {'authorization': api_key}
    response = requests.post('https://api.assemblyai.com/v2/transcript', headers=headers, json={'audio_url': audio_url})

    if response.status_code == 200:
        return response.json().get('id')
    else:
        return None


def poll_transcription(api_key, transcript_id, audio_file):

    headers = {'authorization': api_key}
    while True:
        response = requests.get(f'https://api.assemblyai.com/v2/transcript/{transcript_id}', headers=headers)
        result = response.json()

        if result['status'] == 'completed':
            if os.path.exists(audio_file):
                os.remove(audio_file)

            return result['text']

        elif result['status'] == 'failed':
            raise Exception("Transcription failed.")

        time.sleep(1)

