import os
import cv2
import base64
from werkzeug.utils import secure_filename
from moviepy.editor import VideoFileClip

ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv'}
MAX_FILE_SIZE_MB = 50

def validate_video_file(file):
    """
    Validate video file type and size.
    
    Args:
        file: FileStorage object from Flask request
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not file or not file.filename:
        return False, "No file provided"
    
    # Check file extension
    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
    
    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset pointer
    
    file_size_mb = file_size / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        return False, f"File exceeds {MAX_FILE_SIZE_MB}MB limit (size: {file_size_mb:.2f}MB)"
    
    return True, None


def save_temp_file(file, upload_folder):
    """
    Save uploaded file to temporary location.
    
    Args:
        file: FileStorage object from Flask request
        upload_folder: Directory to save file
        
    Returns:
        tuple: (file_path, filename, file_size_mb)
    """
    os.makedirs(upload_folder, exist_ok=True)
    
    filename = secure_filename(file.filename)
    # Add timestamp to avoid conflicts
    timestamp = str(int(os.times().elapsed * 1000))
    unique_filename = f"{timestamp}_{filename}"
    file_path = os.path.join(upload_folder, unique_filename)
    
    file.save(file_path)
    
    # Get file size
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    
    return file_path, filename, file_size_mb


def extract_audio_from_video(video_path, audio_output_path=None):
    """
    Extract audio from video file using moviepy.
    
    Args:
        video_path: Path to video file
        audio_output_path: Path to save audio (optional)
        
    Returns:
        str: Path to extracted audio file
    """
    if audio_output_path is None:
        base_name = os.path.splitext(video_path)[0]
        audio_output_path = f"{base_name}.wav"
    
    try:
        video = VideoFileClip(video_path)
        video.audio.write_audiofile(audio_output_path, logger=None)
        video.close()
        return audio_output_path
    except Exception as e:
        print(f"Audio extraction failed: {e}")
        raise e


def extract_thumbnail(video_path):
    """
    Extract first frame from video and return as base64 string.
    
    Args:
        video_path: Path to video file
        
    Returns:
        str: Base64 encoded thumbnail as data URI, or None on failure
    """
    try:
        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            # Encode frame as JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            thumbnail_base64 = base64.b64encode(buffer).decode('utf-8')
            return f"data:image/jpeg;base64,{thumbnail_base64}"
        return None
    except Exception as e:
        print(f"Thumbnail extraction failed: {e}")
        return None


def cleanup_files(*file_paths):
    """
    Delete temporary files.
    
    Args:
        *file_paths: Variable number of file paths to delete
    """
    for file_path in file_paths:
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                print(f"Cleaned up: {file_path}")
        except Exception as e:
            print(f"Failed to cleanup {file_path}: {e}")
