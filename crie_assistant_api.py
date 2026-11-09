from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import urllib.parse
from typing import Any, Dict

from normative_search_index import get_normative_index, InvertedIndex


class CRIEAssistantRequestHandler(BaseHTTPRequestHandler):
    index: InvertedIndex = None

    @classmethod
    def init_index(cls, catalog_path: str = None):
        if cls.index is None or not cls.index.is_loaded:
            cls.index = get_normative_index(catalog_path)

    def _set_headers(self, status_code: int = 200, content_type: str = "application/json"):
        self.send_response(status_code)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(204)

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        params = urllib.parse.parse_qs(parsed_url.query)

        if path == "/" or path == "/health":
            payload = {
                "status": "healthy",
                "service": "crie-normative-search",
                "documents_indexed": self.index.total_docs if self.index else 0
            }
            self._set_headers(200)
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            return

        if path == "/api/normative/search":
            query = params.get("q", [""])[0]
            category = params.get("category", [None])[0]
            doc_type = params.get("doc_type", [None])[0]
            specialty = params.get("specialty", [None])[0]
            try:
                limit = int(params.get("limit", [50])[0])
            except ValueError:
                limit = 50

            search_res = self.index.search(
                query=query,
                category=category,
                doc_type=doc_type,
                specialty=specialty,
                limit=limit
            )
            self._set_headers(200)
            self.wfile.write(json.dumps(search_res, ensure_ascii=False).encode("utf-8"))
            return

        if path == "/api/normative/facets":
            # Return overall facets across all loaded documents
            facets = self.index._compute_facets(set(range(self.index.total_docs)))
            payload = {
                "total_documents": self.index.total_docs,
                "facets": facets
            }
            self._set_headers(200)
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            return

        self._set_headers(404)
        self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))


def run_server(port: int = 8080, catalog_path: str = None):
    CRIEAssistantRequestHandler.init_index(catalog_path)
    server_address = ("", port)
    httpd = HTTPServer(server_address, CRIEAssistantRequestHandler)
    print(f"CRIE Assistant API server running on port {port} (Documents: {CRIEAssistantRequestHandler.index.total_docs})")
    httpd.serve_forever()


if __name__ == "__main__":
    run_server()
