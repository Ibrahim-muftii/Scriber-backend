import os
import cv2
import base64
import subprocess
from werkzeug.utils import secure_filename

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
    Extract audio from video file using FFmpeg directly.
    
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
        # Use FFmpeg to extract audio
        command = [
            'ffmpeg',
            '-i', video_path,
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # PCM 16-bit
            '-ar', '16000',  # 16kHz sample rate (good for Whisper)
            '-ac', '1',  # Mono
            '-y',  # Overwrite output file
            audio_output_path
        ]
        
        subprocess.run(command, check=True, capture_output=True)
        return audio_output_path
    except subprocess.CalledProcessError as e:
        print(f"Audio extraction failed: {e.stderr.decode() if e.stderr else str(e)}")
        raise Exception(f"FFmpeg audio extraction failed: {str(e)}")
    except Exception as e:
        print(f"Audio extraction failed: {e}")
        raise e


def extract_thumbnail(video_path, max_width=160, max_height=90, quality=60):
    """
    Extract first frame from video and return as compressed base64 string.
    
    Args:
        video_path: Path to video file
        max_width: Maximum thumbnail width (default 160px)
        max_height: Maximum thumbnail height (default 90px)
        quality: JPEG quality 1-100 (default 60, lower = smaller file)
        
    Returns:
        str: Base64 encoded thumbnail as data URI, or None on failure
    """
    try:
        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            # Get original dimensions
            height, width = frame.shape[:2]
            
            # Calculate scaling to fit within max dimensions while maintaining aspect ratio
            scale = min(max_width / width, max_height / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            # Resize frame
            resized = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            # Encode as JPEG with compression
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
            _, buffer = cv2.imencode('.jpg', resized, encode_params)
            
            thumbnail_base64 = base64.b64encode(buffer).decode('utf-8')
            print(f"Thumbnail size: {len(thumbnail_base64)} chars ({new_width}x{new_height})")
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
