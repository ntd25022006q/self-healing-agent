import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS


class WebSearchTool:
    @staticmethod
    def search(query: str, max_results: int = 3) -> list:
        """
        Perform a search query using DuckDuckGo and return list of dicts with title, href, body.
        """
        results = []
        try:
            with DDGS() as ddgs:
                ddgs_gen = ddgs.text(query, max_results=max_results)
                for r in ddgs_gen:
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", "")
                    })
        except Exception as e:
            # Fallback search or empty results
            print(
                f"[Warning] DuckDuckGo search failed: {e}. Trying fallback search...")
            try:
                # Basic html fallback search
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                response = requests.get(
                    f"https://html.duckduckgo.com/html/?q={query}", headers=headers, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")

                    # Alternative simple parse
                    for a in soup.find_all("a", class_="result__snippet", limit=max_results):
                        parent = a.find_parent("div", class_="result__body")
                        if parent:
                            title_a = parent.find_previous_sibling("h2").find(
                                "a") if parent.find_previous_sibling("h2") else None
                            if title_a:
                                results.append({
                                    "title": title_a.text.strip(),
                                    "url": title_a.get("href", ""),
                                    "snippet": a.text.strip()
                                })
            except Exception as e_fallback:
                print(f"[Error] Fallback search failed: {e_fallback}")

        return results

    @staticmethod
    def scrape_url(url: str) -> str:
        """
        Scrape text content from a URL and convert it to clean text, removing scripts, styles, etc.
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return f"Failed to retrieve page, HTTP Status: {response.status_code}"

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "header", "footer", "nav", "aside"]):
                script.decompose()

            # Extract plain text
            text = soup.get_text()

            # Collapse whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip()
                      for line in lines for phrase in line.split("  "))
            clean_text = "\n".join(chunk for chunk in chunks if chunk)

            # Limit returned content length to prevent token overflow
            return clean_text[:8000]
        except Exception as e:
            return f"Error scraping URL: {str(e)}"

    @classmethod
    def verify_api(cls, library_name: str, function_name: str) -> dict:
        """
        Verifies if a specific function exists in a library by searching PyPI or GitHub documentation.
        Returns verification status and reference snippets.
        """
        query = f"site:pypi.org/project/{library_name} OR site:github.com/ {library_name} {function_name}"
        search_results = cls.search(query, max_results=3)

        verified = False
        reference_text = ""

        # Look for occurrences in the search snippets
        for r in search_results:
            snippet = r["snippet"].lower()
            if function_name.lower() in snippet:
                verified = True
                reference_text += f"Found reference at {r['url']}: {r['snippet']}\n"

        # If not found in snippets, try scraping the first search result
        if not verified and search_results:
            first_url = search_results[0]["url"]
            scraped = cls.scrape_url(first_url)
            if function_name.lower() in scraped.lower():
                verified = True
                # Extract surrounding context of the function name
                pos = scraped.lower().find(function_name.lower())
                start = max(0, pos - 300)
                end = min(len(scraped), pos + 300)
                reference_text += f"Scraped from {first_url}:\n... {scraped[start:end]} ...\n"

        return {
            "verified": verified,
            "query": query,
            "reference": reference_text if verified else "No official documentation reference found. API might be hallucinated."
        }


if __name__ == "__main__":
    # Quick test
    print("Searching for pytest documentation...")
    res = WebSearchTool.search("pytest exit code documentation", max_results=1)
    print(res)
    print("Verifying if geopy has Nominatim...")
    v = WebSearchTool.verify_api("geopy", "Nominatim")
    print(v)
