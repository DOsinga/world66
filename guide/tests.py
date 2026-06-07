import sqlite3
import tempfile
from pathlib import Path

from django.test import Client, SimpleTestCase

from guide import views


class SearchFormatJsonTests(SimpleTestCase):
    def setUp(self):
        self.client = Client()
        self._original_search_db = views.SEARCH_DB

    def tearDown(self):
        views.SEARCH_DB = self._original_search_db

    def test_search_format_json_returns_empty_results_without_query(self):
        response = self.client.get("/search?format=json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response.json(), {"results": []})

    def test_search_format_json_returns_empty_results_without_index(self):
        views.SEARCH_DB = Path("/tmp/world66-missing-search-test.db")

        response = self.client.get("/search?q=Paris&format=json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"results": []})

    def test_search_format_json_uses_search_index(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "search.db"
            conn = sqlite3.connect(db_path)
            try:
                conn.execute("""
                    CREATE VIRTUAL TABLE docs USING fts5(
                        path UNINDEXED, title, body,
                        page_type UNINDEXED, url_path UNINDEXED, location UNINDEXED
                    )
                """)
                conn.execute(
                    """INSERT INTO docs(title, body, page_type, url_path, location)
                       VALUES (?, ?, ?, ?, ?)""",
                    ("Paris", "France travel guide", "location", "europe/france/paris", "France"),
                )
                conn.commit()
            finally:
                conn.close()

            views.SEARCH_DB = db_path
            response = self.client.get("/search?q=par&format=json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "results": [{
                "title": "Paris",
                "url": "/europe/france/paris",
                "page_type": "location",
                "location": "France",
            }],
        })
