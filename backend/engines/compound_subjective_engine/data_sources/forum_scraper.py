import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def fetch_forum_posts(query):
    results_text = []

    # reddit public search (no api)
    reddit_url = f"https://www.reddit.com/search/?q={query}"
    try:
        r = requests.get(reddit_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for post in soup.find_all("h3")[:20]:
            results_text.append(post.get_text())
    except:
        pass

    # longevity forum example (lcity)
    longevity_url = f"https://www.longecity.org/forum/search/?q={query}"
    try:
        r = requests.get(longevity_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for post in soup.find_all("a")[:20]:
            text = post.get_text()
            if len(text) > 20:
                results_text.append(text)
    except:
        pass

    if not results_text:
        return "No subjective discussions found."

    return "\n\n".join(results_text)
