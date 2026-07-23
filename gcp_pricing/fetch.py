import urllib.request
import urllib.error

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}


class FetchError(Exception):
    pass


def fetch(url: str, timeout: int = 40) -> str:
    """Fetch a URL and return decoded text. Raises FetchError with a human message on failure."""
    try:
        req = urllib.request.Request(url, headers=UA)
        return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise FetchError(f"HTTP {e.code} fetching {url}") from e
    except Exception as e:
        raise FetchError(f"could not fetch {url}: {e}") from e
