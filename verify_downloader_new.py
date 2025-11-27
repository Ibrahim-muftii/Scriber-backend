from app.utils.video_downloader import download_video
import os

def test_downloader():
    # Test with a known short video or the user's example
    # Using a random short video for testing
    url = "https://www.youtube.com/watch?v=jNQXAC9IVRw" # Me at the zoo (very short)
    print(f"Testing download for: {url}")
    
    try:
        file_path, title, thumbnail, embed, duration = download_video(url, "test_downloads")
        
        if file_path and os.path.exists(file_path):
            print("[SUCCESS] Download Successful!")
            print(f"File: {file_path}")
            print(f"Title: {title}")
            print(f"Thumbnail: {thumbnail}")
            print(f"Embed: {embed}")
            print(f"Duration: {duration}")
            
            # Clean up
            # os.remove(file_path)
            # os.rmdir("test_downloads")
        else:
            print("[FAILURE] Download Failed: No file returned.")
            
    except Exception as e:
        print(f"[FAILURE] Test Failed with Exception: {e}")

if __name__ == "__main__":
    test_downloader()
