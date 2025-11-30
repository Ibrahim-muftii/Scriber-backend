from youtube_transcript_api import YouTubeTranscriptApi

def get_full_transcription(video_id):
    try:
        print(f"Fetching transcription for video ID: {video_id}")
        api = YouTubeTranscriptApi()
        transcript_list = api.fetch(video_id)
        
        # Combine all text parts into a single string
        full_text = " ".join([t.text for t in transcript_list])
        
        print("\n--- Full Transcription ---")
        print(full_text)
        print("--------------------------\n")
        return full_text
        
    except Exception as e:
        print(f"Error fetching transcription: {e}")
        return None

if __name__ == "__main__":
    # Example video ID (Me at the zoo: jNQXAC9IVRw, or the one you tested: 8-_jt6cgv0U)
    VIDEO_ID = "8-_jt6cgv0U" 
    get_full_transcription(VIDEO_ID)
