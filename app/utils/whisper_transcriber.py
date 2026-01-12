import subprocess
import os
from dotenv import load_dotenv

load_dotenv()

def transcribe_video(audio_path, final_output_path=None):
    """
    Transcribe audio using Whisper CLI.
    Uses tiny model with 2 threads as specified.
    
    Args:
        audio_path: Path to audio file
        final_output_path: Path where transcription output will be saved
        
    Returns:
        str: Transcribed text or empty string on failure
    """
    print(f"Starting transcription for: {audio_path}")
    
    # Get absolute paths
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Log environment variables
    print("=== Environment Variables ===")
    print(f"WHISPER_CLI_PATH (env): {os.getenv('WHISPER_CLI_PATH')}")
    print(f"WHISPER_MODEL_PATH (env): {os.getenv('WHISPER_MODEL_PATH')}")
    print(f"Base directory: {base_dir}")
    print("============================")
    
    # Try to get from environment variables first, fallback to relative paths
    whisper_cli = os.getenv('WHISPER_CLI_PATH')
    model_path = os.getenv('WHISPER_MODEL_PATH')
    
    if not whisper_cli:
        whisper_cli = os.path.join(base_dir, "whisper.cpp/build/bin/whisper-cli")
    if not model_path:
        # Use .en version which is English-only (smaller and faster)
        model_path = os.path.join(base_dir, "whisper.cpp/models/ggml-tiny.en.bin")
    
    # Set default output path
    if final_output_path is None:
        audio_dir = os.path.dirname(audio_path)
        final_output_path = os.path.join(audio_dir, os.path.basename(audio_path) + ".txt")
    
    print(f"Whisper CLI: {whisper_cli}")
    print(f"Model path: {model_path}")
    print(f"Output path: {final_output_path}")
    
    # Verify files exist
    if not os.path.exists(whisper_cli):
        error_msg = f"Whisper CLI not found at: {whisper_cli}"
        print(f"ERROR: {error_msg}")
        return ""
    
    if not os.path.exists(model_path):
        error_msg = f"Whisper model not found at: {model_path}"
        print(f"ERROR: {error_msg}")
        return ""
    
    if not os.path.exists(audio_path):
        error_msg = f"Audio file not found at: {audio_path}"
        print(f"ERROR: {error_msg}")
        return ""
    
    # Make sure whisper-cli is executable
    try:
        os.chmod(whisper_cli, 0o755)
    except:
        pass

    command = [
        whisper_cli,
        "-m", model_path,
        "-f", audio_path,
        "--threads", "2",
        "--language", "en",
        "--output-txt"
    ]
    
    print(f"Running command: {' '.join(command)}")

    try:     
        result = subprocess.run(
            command, 
            check=True, 
            capture_output=True, 
            text=True,
            cwd=base_dir  # Run from base directory
        )
        
        print(f"Whisper STDOUT: {result.stdout}")
        if result.stderr:
            print(f"Whisper STDERR: {result.stderr}")
        
        # Read transcription result
        if os.path.exists(final_output_path):
            with open(final_output_path, "r", encoding="utf-8") as f:
                transcription = f.read().strip()
            
            # Clean up output file
            try:
                os.remove(final_output_path)
            except:
                pass
            
            print(f"Transcription successful: {len(transcription)} characters")
            return transcription
        else:
            print(f"ERROR: Output file not created at: {final_output_path}")
            return ""

    except subprocess.CalledProcessError as e:
        print(f"Transcription command failed with exit code {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return ""
    except Exception as e:
        print(f"Transcription failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return ""
