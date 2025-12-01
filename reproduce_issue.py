import sys
import os
import youtube_transcript_api
from youtube_transcript_api import YouTubeTranscriptApi
import traceback

print("--- ENVIRONMENT CHECK ---")
print(f"Python Executable: {sys.executable}")
print(f"Library Location: {os.path.dirname(youtube_transcript_api.__file__)}")
try:
    print(f"Library Version: {youtube_transcript_api.__version__}")
except AttributeError:
    print("Library Version: <Unknown - __version__ not found>")
print(f"Available attributes: {dir(YouTubeTranscriptApi)}")
print("-------------------------\n")

print("Attempting to fetch transcript for 'jNQXAC9IVRw' (Me at the zoo) using list_transcripts...")

try:
    transcript_list = YouTubeTranscriptApi.list_transcripts("jNQXAC9IVRw")
    print("Transcript list fetched successfully.")
    
    print("Available transcripts:")
    for t in transcript_list:
        print(f" - {t.language} ({t.language_code}) [{'Generated' if t.is_generated else 'Manual'}]")
        
    transcript = transcript_list.find_manually_created_transcript(['en'])
    print("\nFetching Manual English transcript...")
    data = transcript.fetch()
    print("Success!")
    print(data[0])
    
except Exception:
    print("Failed!")
    traceback.print_exc()
