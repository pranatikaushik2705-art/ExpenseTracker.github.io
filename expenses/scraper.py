import requests
from bs4 import BeautifulSoup

def get_live_price(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")

        # Amazon India Price Selector
        price_span = soup.find("span", {"class": "a-price-whole"})
        if price_span:
            # "1,299." ko clean karke float mein badalna
            price_text = price_span.get_text().replace(',', '').replace('.', '')
            return float(price_text)
            
        return None
    except Exception as e:
        print(f"Scraping error: {e}")
        return None