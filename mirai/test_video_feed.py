import requests
import time

def test_video_feed():
    url = 'http://127.0.0.1:8000/studio/video_feed'
    print(f"Connecting to {url}...")
    try:
        with requests.get(url, stream=True, timeout=5) as r:
            print(f"Status Code: {r.status_code}")
            print(f"Headers: {r.headers}")
            
            if r.status_code == 200:
                print("Reading stream...")
                start = time.time()
                bytes_read = 0
                for chunk in r.iter_content(chunk_size=1024):
                    bytes_read += len(chunk)
                    if bytes_read > 100000: # Read ~100KB
                        print(f"Successfully read {bytes_read} bytes.")
                        break
                    if time.time() - start > 5:
                        print("Timeout reading stream.")
                        break
            else:
                print("Failed to connect.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_video_feed()
