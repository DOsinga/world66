import base64
import json
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings


def _headers(accept="application/vnd.github+json"):
    headers = {
        "Accept": accept,
        "User-Agent": "World66Preview/1.0",
    }
    token = getattr(settings, "GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _url(path):
    repo = getattr(settings, "GITHUB_REPO", "DOsinga/world66")
    return f"https://api.github.com/repos/{repo}{path}"


def _quote_path(path):
    return "/".join(quote(part) for part in path.strip("/").split("/") if part)


def _request_json(url):
    request = Request(url, headers=_headers())
    try:
        with urlopen(request, timeout=getattr(settings, "GITHUB_TIMEOUT", 10)) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None


def _request_bytes(url):
    request = Request(url, headers=_headers("application/vnd.github.raw"))
    try:
        with urlopen(request, timeout=getattr(settings, "GITHUB_TIMEOUT", 10)) as response:
            return response.read()
    except (HTTPError, URLError, TimeoutError):
        return None


@lru_cache(maxsize=512)
def resolve_commit(ref):
    data = _request_json(_url(f"/commits/{quote(ref, safe='')}"))
    if not isinstance(data, dict):
        return ""
    sha = data.get("sha", "")
    return sha if len(sha) == 40 else ""


def short_hash(full_hash):
    return full_hash[:10]


@lru_cache(maxsize=4096)
def _get_contents(ref, content_path):
    full_hash = resolve_commit(ref) or ref
    quoted_path = _quote_path(content_path)
    return _request_json(_url(f"/contents/{quoted_path}?ref={quote(full_hash, safe='')}"))


@lru_cache(maxsize=4096)
def get_file_bytes(ref, content_path):
    data = _get_contents(ref, content_path)
    if not isinstance(data, dict) or data.get("type") != "file":
        return None

    encoded = data.get("content")
    if isinstance(encoded, str):
        try:
            return base64.b64decode(encoded)
        except ValueError:
            return None

    download_url = data.get("download_url")
    if download_url:
        return _request_bytes(download_url)
    return None


def get_file_text(ref, content_path):
    data = get_file_bytes(ref, content_path)
    if data is None:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


@lru_cache(maxsize=4096)
def list_dir(ref, content_path):
    data = _get_contents(ref, content_path)
    if not isinstance(data, list):
        return []
    return [
        {
            "name": item.get("name", ""),
            "path": item.get("path", ""),
            "type": item.get("type", ""),
        }
        for item in data
        if item.get("name") and item.get("path")
    ]


def file_exists(ref, content_path):
    data = _get_contents(ref, content_path)
    return isinstance(data, dict) and data.get("type") == "file"


def iter_files(ref, content_path):
    stack = [content_path.strip("/")]
    while stack:
        current = stack.pop()
        for item in list_dir(ref, current):
            if item["type"] == "dir":
                stack.append(item["path"])
            elif item["type"] == "file":
                yield item["path"]
