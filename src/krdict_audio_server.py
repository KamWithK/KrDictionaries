import json
import unicodedata

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from http import HTTPStatus
from socketserver import TCPServer
from threading import Thread

# NOTE - Inspired by Forvo audio Anki extension's code
# Source - https://github.com/jamesnicolas/yomichan-forvo-server/blob/c5c2d897c79565702e4034a4cc35ca71c64dd580/__init__.py

DICTIONARY_PATH = "dictionaries/krdict_korean_korean.json"

with open(DICTIONARY_PATH, "r", encoding="utf-8") as file:
    dictionary = json.load(file)

def has_audio(entry):
    return entry["audio_url"] not in ["", None]

def word_match(word: str, hanja: str, entry):
    word_satisfied = entry["word"] == word
    hanja_satisfied = hanja == entry["hanja"] or hanja in ["", None]# or entry["hanja"] in ["", None]

    return word_satisfied and hanja_satisfied

def word_audio(word: str, hanja: str=""):
    return [{
        "name": entry["hanja"] + " - " + entry["word"],
        "url": entry["audio_url"]
    } for entry in dictionary if has_audio(entry) and word_match(word, hanja, entry)]

class AudioServer(SimpleHTTPRequestHandler):
    # By default, SimpleHTTPRequestHandler logs to stderr
    # This would cause Anki to show an error, even on successful requests
    # log_error is still a useful function though, so replace it with the inherited log_message
    # Make log_message do nothing
    def log_error(self, *args, **kwargs):
        super().log_message(*args, **kwargs)

    def log_message(self, *args):
        pass

    def do_GET(self):
        query_components = parse_qs(urlparse(self.path).query)

        # Support expression or term
        term = ""
        if "expression" in query_components:
            term = query_components["expression"][0]
        if "term" in query_components:
            term = query_components["term"][0]

        reading = query_components["reading"][0] if "reading" in query_components else ""

        # Yomichan formatted response
        response = {
            "type": "audioSourceList",
            "audioSources": word_audio(reading, term)
        }

        # UTF-8 encoded JSON response
        payload = bytes(json.dumps(response), "utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-type", "application/json")
        self.send_header("Content-length", str(len(payload)))
        self.end_headers()
        try:
            self.wfile.write(payload)
        except BrokenPipeError:
            self.log_error("BrokenPipe when sending reply")

        return

# Run within this thread if run on its own or on a new thread otherwise
if __name__ == "__main__":
    httpd = TCPServer(("localhost", 8770), AudioServer)
    httpd.serve_forever()
else:
    from aqt import mw
    httpd = ThreadingHTTPServer(("localhost", 8770), AudioServer)
    server_thread = Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()
