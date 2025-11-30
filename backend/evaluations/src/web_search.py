import requests

def duckduckgo_search(query, max_results=5):
    url = "https://duckduckgo-api.vercel.app/search"
    try:
        data = requests.get(url, params={"q": query}).json()
        return [res["snippet"] for res in data["results"][:max_results]]
    except:
        return []
