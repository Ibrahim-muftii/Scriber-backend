import requests
from youtube_transcript_api import YouTubeTranscriptApi
import re

def parse_duration(duration_str):
    """
    Parse ISO 8601 duration string (e.g., PT1H2M10S) to seconds.
    """
    try:
        match = re.search(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
        if not match:
            return 0
            
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        return (hours * 3600) + (minutes * 60) + seconds
    except Exception:
        return 0

def test():
    print("Starting Proxy Connection Diagnostics")
    
    # Webshare configuration
    proxy_user = "cxjfcrft-1"
    proxy_pass = "y4mi69ni1mxg"
    
    # Test different Webshare endpoints
    test_configs = [
        {"host": "p.webshare.io", "port": "80"},
        {"host": "proxy.webshare.io", "port": "80"},
        {"host": "p.webshare.io", "port": "9999"},
        {"host": "proxy.webshare.io", "port": "9999"},
    ]
    
    for idx, config in enumerate(test_configs, 1):
        proxy_host = config["host"]
        proxy_port = config["port"]
        
        print(f"\n{'='*60}")
        print(f"Test Configuration {idx}/{len(test_configs)}")
        print(f"Target Proxy: {proxy_host}:{proxy_port}")
        print(f"User: {proxy_user}")
        print(f"Pass: {'*' * len(proxy_pass)}")
        print(f"{'='*60}")
        
        proxy_url = f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        
        session = requests.Session()
        session.proxies.update(proxies)
        
        # Test HTTP
        print("\n--- HTTP Request (http://httpbin.org/ip) ---")
        try:
            resp = session.get("http://httpbin.org/ip", timeout=10)
            print(f"Status Code: {resp.status_code}")
            if resp.status_code == 200:
                print(f"[SUCCESS] Origin IP: {resp.json().get('origin')}")
                print(f"\n*** WORKING CONFIG: {proxy_host}:{proxy_port} ***\n")
                return  # Found working config, exit
            elif resp.status_code == 407:
                print("[FAIL] 407 Proxy Authentication Required")
            else:
                print(f"[FAIL] Unexpected status: {resp.status_code}")
        except Exception as e:
            print(f"[FAIL] Exception: {str(e)[:100]}")
    
    print("\n" + "="*60)
    print("All configurations failed. Please verify:")
    print("1. Username and password are correct")
    print("2. Your IP is authorized in Webshare dashboard (if required)")
    print("3. Check Webshare dashboard for correct proxy endpoint")
    print("="*60)

if __name__ == "__main__":
    test()