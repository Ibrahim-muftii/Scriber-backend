import subprocess
import os

def transcribe_video(audio_path, final_output_path="uploads/audio/audio.wav.txt"):
    """
    Transcribe audio using Whisper CLI.
    Uses tiny model with 2 threads as specified.
    
    Args:
        audio_path: Path to audio file
        final_output_path: Path where transcription output will be saved
        
    Returns:
        str: Transcribed text or empty string on failure
    """
    print("transcribing the video")
    model_path = "whisper.cpp/models/ggml-tiny.bin"
    whisper_cli = "whisper.cpp/build/bin/whisper-cli"

    command = [
        whisper_cli,
        "-m", model_path,
        "-f", audio_path,
        "--threads", "2",
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
