import os
import time
import re
import requests
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

def download_video(youtube_url, output_path='videos'):
    """
    Downloads a video from YouTube using SaveFrom.net via Playwright.
    Scrapes metadata from YouTube first.
    Returns: (file_path, title, thumbnail_url, embedded_url, duration)
    """
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        page = context.new_page()
        stealth = Stealth()
        stealth.apply_stealth_sync(page)

        # 1. Scrape Metadata from YouTube
        print(f"[INFO] Scraping metadata for: {youtube_url}")
        title = "Unknown Video"
        thumbnail_url = ""
        embedded_url = ""
        duration = 0
        
        try:
            page.goto(youtube_url, wait_until="domcontentloaded")
            # Wait a bit for title to load
            try:
                page.wait_for_selector("h1.ytd-watch-metadata", timeout=5000)
                title_el = page.query_selector("h1.ytd-watch-metadata")
                if title_el:
                    title = title_el.inner_text().strip()
            except:
                # Fallback to page title
                title = page.title().replace(" - YouTube", "")

            # Get video ID for thumbnail/embed
            video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", youtube_url)
            video_id = video_id_match.group(1) if video_id_match else ""
            
            if video_id:
                thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                embedded_url = f"https://www.youtube.com/embed/{video_id}"
            
        except Exception as e:
            print(f"[WARN] Failed to scrape metadata: {e}")

        # 2. Download from SaveFrom.net
        print("[INFO] Navigating to SaveFrom.net...")
        save_path = None
        try:
            page.goto("https://en.savefrom.net/1-youtube-video-downloader-360/", wait_until="domcontentloaded", timeout=60000)
            
            # Input URL
            page.fill("#sf_url", youtube_url)
            page.keyboard.press("Enter")
            
            # Wait for result
            print("[INFO] Waiting for download links...")
            try:
                page.wait_for_selector(".def-btn-box, .result-box", timeout=30000)
            except:
                print("[WARN] Result box not found. Clicking submit button...")
                page.click("#sf_submit")
                page.wait_for_selector(".def-btn-box, .result-box", timeout=30000)
            
            # Check for the main download button first
            download_btn = page.query_selector(".link-download")
            download_url = None
            if download_btn:
                download_url = download_btn.get_attribute("href")
                
            print(f"[INFO] Found download button. URL: {download_url}")
            
            # Try direct download if URL is valid
            if download_url and download_url.startswith("http"):
                print("[INFO] Attempting direct download via requests...")
                try:
                    # Sanitize filename
                    safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).strip()
                    if not safe_title:
                        safe_title = f"video_{int(time.time())}"
                    filename = f"{safe_title}.mp4"
                    save_path = os.path.join(output_path, filename)
                    
                    response = requests.get(download_url, stream=True, headers={"User-Agent": "Mozilla/5.0"})
                    if response.status_code == 200:
                        with open(save_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        print(f"[SUCCESS] Downloaded to: {save_path}")
                        browser.close()
                        return save_path, title, thumbnail_url, embedded_url, duration
                    else:
                        print(f"[WARN] Direct download failed with status {response.status_code}")
                except Exception as e:
                    print(f"[WARN] Direct download failed: {e}")

            # Fallback to clicking
            # Handle popups
            def handle_popup(popup):
                print("[INFO] Popup detected. Closing...")
                try:
                    popup.close()
                except:
                    pass
            page.on("popup", handle_popup)
            
            print(f"[INFO] Starting download via click...")
            
            with page.expect_download(timeout=60000) as download_info:
                # Click the download button. 
                if download_btn:
                    download_btn.click()
                    print("[INFO] Clicked once. Waiting 5s...")
                    time.sleep(5)
                    
                    print("[INFO] Clicking again...")
                    try:
                        download_btn.click()
                    except:
                        pass
                else:
                    links = page.query_selector_all("a.download-icon")
                    if links:
                        links[0].click()
                    else:
                        raise Exception("No download button found")

            download = download_info.value
            
            # Sanitize filename
            safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).strip()
            if not safe_title:
                safe_title = f"video_{int(time.time())}"
            
            filename = f"{safe_title}.mp4"
            save_path = os.path.join(output_path, filename)
            
            # Save the file
            download.save_as(save_path)
            print(f"[SUCCESS] Downloaded to: {save_path}")
            
        except Exception as e:
            print(f"[ERROR] Download failed: {e}")
            # Take screenshot for debug if needed
            page.screenshot(path="debug_error.png")
            return None, None, None, None, None
        finally:
            browser.close()

        return save_path, title, thumbnail_url, embedded_url, duration
