import os
import time
import threading
from flask import Blueprint, request, jsonify
from google import generativeai as genai
from dotenv import load_dotenv
from app.utils.hmac_auth import verify
from app.utils.video_utils import (
    validate_video_file, 
    save_temp_file, 
    extract_audio_from_video,
    extract_thumbnail,
    cleanup_files
)
from app.utils.whisper_transcriber import transcribe_video

load_dotenv()
vt_bp = Blueprint('vt_bp', __name__)

# Configure Gemini AI
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# Storage for processing results (in-memory)
processing_results = {}
processing_lock = threading.Lock()


def process_single_video(video_file, video_id):
    """
    Process a single video in background thread.
    Extracts thumbnail, audio, transcribes, and summarizes.
    
    Args:
        video_file: Tuple of (file_path, original_filename, file_size_mb)
        video_id: Unique identifier for this video
    """
    file_path, original_filename, file_size_mb = video_file
    audio_path = None
    start_time = time.time()
    
    try:
        print(f"Processing video: {original_filename}")
        
        # Extract thumbnail
        print(f"Extracting thumbnail for {original_filename}")
        thumbnail = extract_thumbnail(file_path)
        
        # Extract audio
        print(f"Extracting audio from {original_filename}")
        audio_path = extract_audio_from_video(file_path)
        
        # Transcribe
        print(f"Transcribing {original_filename}")
        transcription = transcribe_video(audio_path)
        
        if not transcription:
            raise Exception("Transcription returned empty result")
        
        # Summarize using Gemini
        print(f"Generating summary for {original_filename}")
        # summary = generate_summary(transcription)
        summary = ""  # Summary generation disabled
        
        processing_time = round(time.time() - start_time, 2)
        
        # Store result
        with processing_lock:
            processing_results[video_id] = {
                'status': 'completed',
                'filename': original_filename,
                'thumbnail': thumbnail,
                'transcription': transcription,
                'summary': summary,
                'file_size_mb': round(file_size_mb, 2),
                'processing_time': processing_time
            }
        
        print(f"✓ Completed processing {original_filename} in {processing_time}s")
        
    except Exception as e:
        print(f"✗ Error processing {original_filename}: {e}")
        with processing_lock:
            processing_results[video_id] = {
                'status': 'error',
                'filename': original_filename,
                'error': str(e),
                'file_size_mb': round(file_size_mb, 2)
            }
    
    finally:
        # Cleanup temp files
        cleanup_files(file_path, audio_path)


def generate_summary(content):
    """
    Generate summary using Gemini AI.
    
    Args:
        content: Transcription text to summarize
        
    Returns:
        str: HTML formatted summary
    """
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
        {content}
        \"\"\"
    """
    
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        summarization = model.generate_content(prompt).text
        # Remove markdown code blocks if present
        import re
        cleaned_summary = re.sub(r"```[\s\S]*?\n([\s\S]*?)```", r"\1", summarization)
        return cleaned_summary
    except Exception as e:
        print(f"Summary generation failed: {e}")
        return f"<p>Summary generation failed: {str(e)}</p>"


@vt_bp.route('/test', methods=['GET', 'POST'])
def test_endpoint():
    """
    Simple test endpoint to verify server is accessible.
    """
    return jsonify({
        'status': 'success',
        'message': 'Video transcription endpoint is working',
        'timestamp': time.time()
    }), 200


@vt_bp.route('/upload-videos', methods=['POST'])
def upload_videos():
    """
    Upload and process single or multiple videos.
    Validates HMAC signature, file sizes, and processes videos in background.
    
    Returns:
        JSON response with processing status
    """
    try:
        # Validate HMAC signature
        timestamp = request.headers.get('X-Timestamp')
        signature = request.headers.get('X-Signature')
        
        print(f"Received upload request - Timestamp: {timestamp}, Signature: {signature}")
        
        if not timestamp or not signature:
            print("Missing authentication headers")
            return jsonify({'error': 'Missing authentication headers'}), 401
        
        # Get the payload (user ID) from request form data
        # Frontend sends this as part of the signature
        user_id = request.form.get('userId', '')
        print(f"User ID from request: '{user_id}'")
        
        # Verify with the actual payload (user ID)
        if not verify(user_id, timestamp, signature):
            print(f"HMAC verification failed")
            print(f"  Expected payload: '{user_id}'")
            print(f"  Timestamp: {timestamp}")
            return jsonify({'error': 'Invalid signature'}), 401
        
        print("✓ HMAC verification successful")
        
        # Get uploaded files
        files = request.files.getlist('videos')
        
        if not files or len(files) == 0:
            return jsonify({'error': 'No videos provided'}), 400
        
        valid_videos = []
        rejected_videos = []
        
        # Validate and save files
        for file in files:
            is_valid, error_msg = validate_video_file(file)
            
            if not is_valid:
                rejected_videos.append({
                    'filename': file.filename,
                    'reason': error_msg
                })
                continue
            
            try:
                # Save file temporarily
                file_path, original_filename, file_size_mb = save_temp_file(
                    file, 
                    'uploads/videos'
                )
                valid_videos.append((file_path, original_filename, file_size_mb))
            except Exception as e:
                rejected_videos.append({
                    'filename': file.filename,
                    'reason': f'Failed to save file: {str(e)}'
                })
        
        if len(valid_videos) == 0:
            return jsonify({
                'status': 'error',
                'message': 'No valid videos to process',
                'rejected': rejected_videos
            }), 400
        
        # Process videos in background threads
        video_ids = []
        threads = []
        
        for idx, video_file in enumerate(valid_videos):
            video_id = f"{int(time.time() * 1000)}_{idx}"
            video_ids.append(video_id)
            
            # Initialize processing status
            with processing_lock:
                processing_results[video_id] = {
                    'status': 'processing',
                    'filename': video_file[1]
                }
            
            # Start background thread
            thread = threading.Thread(
                target=process_single_video,
                args=(video_file, video_id),
                daemon=True
            )
            thread.start()
            threads.append(thread)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Collect results
        results = []
        for video_id in video_ids:
            with processing_lock:
                result = processing_results.get(video_id)
                if result:
                    results.append(result)
                    # Clean up from memory
                    del processing_results[video_id]
        
        return jsonify({
            'status': 'success',
            'message': f'Processed {len(results)} video(s)',
            'results': results,
            'rejected': rejected_videos if rejected_videos else []
        }), 200
        
    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500
