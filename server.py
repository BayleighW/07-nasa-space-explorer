import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen


NASA_API_URL = "https://api.nasa.gov/planetary/apod"
EARLIEST_DATE = date(1995, 6, 16)


class ApodPageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.image_url = None
        self.title = None
        self.video_url = None
        self.explanation_parts = []
        self.reading_explanation = False

    def handle_starttag(self, tag, attributes):
        metadata = dict(attributes)

        if tag in ("iframe", "video") and is_video_url(metadata.get("src", "")):
            self.video_url = metadata["src"]

        if tag == "img":
            image_source = metadata.get("src", "")
            if "/content/dam/science/cds/apod/apod/" in image_source:
                self.image_url = image_source
            return

        if tag == "meta":
            property_name = metadata.get("property", "").lower()
            content = metadata.get("content", "")

            if property_name == "og:image" and "/content/dam/science/cds/apod/apod/" in content:
                self.image_url = content
            elif property_name == "og:title":
                self.title = content
            elif property_name.startswith("og:video") and is_video_url(content):
                self.video_url = content

    def handle_data(self, data):
        text = " ".join(data.split())
        if not text:
            return

        if text == "Explanation:":
            self.reading_explanation = True
            return

        if self.reading_explanation:
            if text in ("Free Presentation:", "Date", "Credit", "Authors & editors:"):
                self.reading_explanation = False
                return
            self.explanation_parts.append(data)


def is_video_url(url):
    parsed_url = urlparse(url)
    video_hosts = ("youtube.com", "youtube-nocookie.com", "vimeo.com")
    video_formats = (".mp4", ".webm", ".m3u8")
    return (
        parsed_url.scheme in ("http", "https")
        and (parsed_url.hostname or "").endswith(video_hosts)
        or parsed_url.path.lower().endswith(video_formats)
    )


class SpaceExplorerHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        request_url = urlparse(self.path)
        if request_url.path == "/api/apod":
            self.handle_apod(parse_qs(request_url.query))
            return

        super().do_GET()

    def handle_apod(self, query):
        start_date = query.get("start_date", [""])[0]
        end_date = query.get("end_date", [""])[0]

        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
        except ValueError:
            self.send_json(400, {"msg": "Choose valid start and end dates."})
            return

        if start < EARLIEST_DATE or end > date.today() or start > end:
            self.send_json(400, {"msg": "Choose a date range supported by NASA APOD."})
            return

        api_query = urlencode({
            "api_key": os.environ.get("NASA_API_KEY", "DEMO_KEY"),
            "start_date": start_date,
            "end_date": end_date,
        })
        api_request = Request(f"{NASA_API_URL}?{api_query}", headers={"User-Agent": "Space Explorer"})

        try:
            with urlopen(api_request, timeout=30) as response:
                apod_data = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            try:
                error_data = json.loads(error.read().decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                error_data = {"msg": "NASA APOD could not return these dates."}

            error_message = error_data.get("error", {}).get("message", "").lower()
            if error.code == 429 or "rate limit" in error_message:
                archive_items = self.get_archive_items(start, end)
                if archive_items:
                    self.send_json(200, archive_items)
                    return
                self.send_json(502, {"msg": "NASA's API is rate-limited and archive entries could not be loaded."})
                return

            self.send_json(error.code, error_data)
            return
        except (URLError, TimeoutError, ValueError) as error:
            self.send_json(502, {"msg": f"Could not reach NASA APOD: {error}"})
            return

        items = apod_data if isinstance(apod_data, list) else [apod_data]

        # Repair placeholder image links using the official APOD archive page.
        with ThreadPoolExecutor(max_workers=5) as executor:
            list(executor.map(self.repair_image, items))

        self.send_json(200, apod_data)

    def get_archive_items(self, start, end):
        apod_dates = []
        current_date = start
        while current_date <= end:
            apod_dates.append(current_date)
            current_date = date.fromordinal(current_date.toordinal() + 1)

        with ThreadPoolExecutor(max_workers=5) as executor:
            items = executor.map(self.get_archive_item, apod_dates)
            return [item for item in items if item]

    def get_archive_item(self, apod_date):
        archive_date = apod_date.strftime("%y%m%d")
        archive_url = f"https://apod.nasa.gov/apod/ap{archive_date}.html"
        page_request = Request(archive_url, headers={"User-Agent": "Space Explorer"})

        try:
            with urlopen(page_request, timeout=20) as response:
                parser = ApodPageParser()
                parser.feed(response.read().decode("utf-8", "replace"))
        except (URLError, TimeoutError) as error:
            print(f"Could not load APOD archive for {apod_date}: {error}")
            return None

        if not parser.image_url and not parser.video_url:
            return None

        title = parser.title or f"Astronomy Picture of the Day - {apod_date.isoformat()}"
        title = title.removeprefix("APOD: ").removesuffix(" - NASA Science")
        explanation = re.sub(r"\s+", " ", "".join(parser.explanation_parts)).strip()
        explanation = re.sub(r"\s+([,.;:!?])", r"\1", explanation)
        explanation = re.sub(r"([([])\s+", r"\1", explanation)
        explanation = re.sub(r"\s+([)\]])", r"\1", explanation)

        if parser.video_url:
            return {
                "date": apod_date.isoformat(),
                "title": title,
                "explanation": explanation,
                "media_type": "video",
                "url": parser.video_url,
            }

        return {
            "date": apod_date.isoformat(),
            "title": title,
            "explanation": explanation,
            "media_type": "image",
            "url": parser.image_url,
            "hdurl": parser.image_url,
        }

    def repair_image(self, item):
        if item.get("media_type") != "image":
            return

        image_urls = [item.get("url", ""), item.get("hdurl", "")]
        has_real_image = any(url and "nasa-logo@2x.png" not in url for url in image_urls)
        if has_real_image:
            return

        try:
            apod_date = date.fromisoformat(item["date"])
            archive_date = apod_date.strftime("%y%m%d")
            archive_url = f"https://apod.nasa.gov/apod/ap{archive_date}.html"
            page_request = Request(archive_url, headers={"User-Agent": "Space Explorer"})

            with urlopen(page_request, timeout=20) as response:
                parser = ApodPageParser()
                parser.feed(response.read().decode("utf-8", "replace"))

            if parser.image_url:
                item["url"] = parser.image_url
                item["hdurl"] = parser.image_url

            if parser.title:
                title = parser.title.removeprefix("APOD: ").removesuffix(" - NASA Science")
                item["title"] = title
        except (KeyError, ValueError, URLError, TimeoutError) as error:
            print(f"Could not repair APOD image for {item.get('date', 'unknown date')}: {error}")

    def send_json(self, status_code, data):
        response_body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(response_body)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8000), SpaceExplorerHandler)
    print("Space Explorer is running at http://localhost:8000")
    server.serve_forever()