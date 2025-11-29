import sys
import os
import time

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def final_check():
    print("--- Starting Final Pre-Deployment Check ---")
    
    # 1. Check Imports
    print("\n1. Checking Imports...")
    try:
        import yt_dlp
        print("   [PASS] yt-dlp is installed and importable.")
    except ImportError as e:
        print(f"   [FAIL] yt-dlp import failed: {e}")
        return

    try:
        from playwright.sync_api import sync_playwright
        print("   [PASS] playwright is installed and importable.")
    except ImportError as e:
        print(f"   [FAIL] playwright import failed: {e}")
        return

    try:
        from app.routes.YoutubeVideoSummarizer import download_youtube_audio
        print("   [PASS] YoutubeVideoSummarizer module imported successfully.")
    except Exception as e:
        print(f"   [FAIL] YoutubeVideoSummarizer import failed: {e}")
        return

    # 2. Check Playwright Browser
    print("\n2. Checking Playwright Browser...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            print("   [PASS] Chromium launched successfully.")
            browser.close()
    except Exception as e:
        print(f"   [FAIL] Playwright browser launch failed: {e}")
        print("          Run 'playwright install chromium' to fix this.")
        return

    # 3. Quick Download Test (Optional but recommended)
    print("\n3. Quick Download Test...")
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw" # Me at the zoo
    output_folder = "final_test_videos"
    try:
        audio_path, _, _, _, _ = download_youtube_audio(test_url, output_path=output_folder)
        if audio_path and os.path.exists(audio_path):
            print(f"   [PASS] Download successful: {audio_path}")
            # Cleanup
            os.remove(audio_path)
            os.rmdir(output_folder)
            print("   [PASS] Cleanup successful.")
        else:
            print("   [FAIL] Download returned invalid path or file missing.")
    except Exception as e:
        print(f"   [FAIL] Download test failed: {e}")

    print("\n--- Check Complete ---")

if __name__ == "__main__":
    final_check()
