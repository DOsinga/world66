from unittest import mock

from django.test import SimpleTestCase, override_settings


class AnalyticsTagTest(SimpleTestCase):
    @override_settings(
        GA_MEASUREMENT_ID="G-TEST123",
        GTM_CONTAINER_ID="GTM-OLD123",
    )
    def test_direct_ga4_tag_prevents_duplicate_gtm_tracking(self):
        response = self.client.get("/search")

        self.assertContains(response, "gtag/js?id=G-TEST123")
        self.assertContains(response, "gtag('config', 'G\\u002DTEST123')")
        self.assertNotContains(response, "gtm.js?id=GTM-OLD123")
        self.assertNotContains(response, "ns.html?id=GTM-OLD123")


class DestinationPoiAggregationTest(SimpleTestCase):
    def test_opted_in_destination_section_lists_flat_pois(self):
        response = self.client.get(
            "/northamerica/netherlandsantilles/bonaire/things_to_do"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bonaire National Marine Park")
        self.assertContains(response, "1000 Steps")
        self.assertContains(response, "Cadushy Distillery")


class SuggestPickTest(SimpleTestCase):
    """The recommend-a-place form is an open write path; these are the locks."""

    PAGE = "southamerica/chile/sanpedrodeatacama"

    def _form(self, **overrides):
        from django.core import signing
        import time
        fields = {
            "form_token": signing.dumps(
                {"path": self.PAGE, "t": int(time.time()) - 30}, salt="pick-suggest"),
            "place": "Laguna Cejar",
            "tip": "Float in it at the end of the day, when the tour buses have gone.",
            "name": "A reader",
        }
        fields.update(overrides)
        return {k: v for k, v in fields.items() if v is not None}

    def test_get_is_rejected(self):
        self.assertEqual(self.client.get("/picks/suggest").status_code, 405)

    def test_honeypot_is_accepted_and_dropped(self):
        with mock.patch("guide.github.create_issue") as create:
            response = self.client.post("/picks/suggest", self._form(website="http://spam"))

        self.assertEqual(response.status_code, 200)
        create.assert_not_called()

    def test_unsigned_path_is_rejected(self):
        with mock.patch("guide.github.create_issue") as create:
            response = self.client.post("/picks/suggest", self._form(form_token=self.PAGE))

        self.assertEqual(response.status_code, 400)
        create.assert_not_called()

    def test_instant_submission_is_rejected(self):
        from django.core import signing
        import time
        token = signing.dumps({"path": self.PAGE, "t": int(time.time())}, salt="pick-suggest")
        with mock.patch("guide.github.create_issue") as create:
            response = self.client.post("/picks/suggest", self._form(form_token=token))

        self.assertEqual(response.status_code, 400)
        create.assert_not_called()

    def test_the_age_check_cannot_be_forged(self):
        """The issue time is inside the signature, so backdating it does nothing."""
        from django.core import signing
        import time
        fresh = signing.dumps({"path": self.PAGE, "t": int(time.time())}, salt="pick-suggest")
        with mock.patch("guide.github.create_issue") as create:
            # A bot's best move under the old design: claim the form is old.
            response = self.client.post("/picks/suggest", self._form(
                form_token=fresh, form_ts=str(int(time.time()) - 3600)))

        self.assertEqual(response.status_code, 400)
        create.assert_not_called()

    def test_nothing_a_reader_types_can_add_contact_details(self):
        """There is no contact field, so none can reach a public issue."""
        with mock.patch("guide.github.create_issue", return_value="https://x/1") as create:
            self.client.post("/picks/suggest", self._form(contact="me@example.com"))

        self.assertNotIn("me@example.com", create.call_args.args[1])

    def test_forwarded_for_does_not_choose_the_rate_limit_bucket(self):
        """A spoofed header must not hand a bot a fresh bucket."""
        from guide import views
        self.assertEqual(
            views._client_ip(type("R", (), {"META": {
                "HTTP_X_FORWARDED_FOR": "1.2.3.4", "REMOTE_ADDR": "10.0.0.9"}})()),
            "10.0.0.9")

    def test_missing_tip_is_rejected(self):
        with mock.patch("guide.github.create_issue") as create:
            response = self.client.post("/picks/suggest", self._form(tip=""))

        self.assertEqual(response.status_code, 400)
        create.assert_not_called()

    def test_good_submission_files_an_issue_naming_the_signed_page(self):
        with mock.patch("guide.github.create_issue", return_value="https://github.com/x/y/issues/1") as create:
            response = self.client.post("/picks/suggest", self._form())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["url"], "https://github.com/x/y/issues/1")
        title, body = create.call_args.args[0], create.call_args.args[1]
        self.assertIn("Laguna Cejar", title)
        self.assertIn(self.PAGE, body)
        self.assertIn("pick-suggestion", create.call_args.kwargs["labels"])

    def test_location_page_offers_the_form(self):
        response = self.client.get("/" + self.PAGE)

        self.assertContains(response, "Recommend a place")
        self.assertContains(response, 'action="/picks/suggest"')
