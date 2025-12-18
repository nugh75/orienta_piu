import requests

def test_conn():
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    print("Testing Google...")
    try:
        r = requests.get("https://www.google.com/search?q=test", headers=headers, timeout=5)
        print(f"Google Status: {r.status_code}")
    except Exception as e:
        print(f"Google Error: {e}")

    print("Testing Bing...")
    try:
        r = requests.get("https://www.bing.com/search?q=test", headers=headers, timeout=5)
        print(f"Bing Status: {r.status_code}")
    except Exception as e:
        print(f"Bing Error: {e}")

if __name__ == "__main__":
    test_conn()
