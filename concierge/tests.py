import json
from unittest import mock

from django.test import RequestFactory, SimpleTestCase, override_settings

from concierge import agent, views
from concierge.preview import COOKIE_NAME, make_token

CITY = "/northamerica/nicaragua/granada"
COUNTRY = "/northamerica/nicaragua"


def unlocked(test):
    test.client.cookies[COOKIE_NAME] = make_token()


@override_settings(CONCIERGE_PREVIEW_KEY="open-sesame")
class PreviewToggleTest(SimpleTestCase):
    def test_the_unlock_page_needs_the_key(self):
        self.assertEqual(self.client.get("/concierge/preview").status_code, 404)
        self.assertEqual(self.client.get("/concierge/preview?key=guess").status_code, 404)

        response = self.client.get("/concierge/preview?key=open-sesame")

        self.assertEqual(response.status_code, 200)
        self.assertIn(COOKIE_NAME, response.cookies)

    def test_an_ordinary_visitor_never_receives_the_overlay(self):
        response = self.client.get(CITY)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "concierge-panel")
        self.assertNotContains(response, "Plan your trip with our concierge")

    def test_a_previewer_sees_it(self):
        unlocked(self)

        response = self.client.get(CITY)

        self.assertContains(response, "Plan your trip with our concierge")
        self.assertContains(response, "concierge.js")

    def test_a_forged_cookie_does_not_unlock_it(self):
        self.client.cookies[COOKIE_NAME] = "on"

        self.assertNotContains(self.client.get(CITY), "Plan your trip with our concierge")


@override_settings(CONCIERGE_PREVIEW_KEY="open-sesame")
class WhereTheButtonAppearsTest(SimpleTestCase):
    def setUp(self):
        unlocked(self)

    def test_it_is_on_destinations_poi_lists_and_pois(self):
        for path in (CITY,
                     CITY + "/eating_out",
                     "/northamerica/nicaragua/isla_ometepe"):
            with self.subTest(path=path):
                self.assertContains(self.client.get(path), "Plan your trip with our concierge")

    def test_it_is_not_on_countries_continents_or_the_home_page(self):
        for path in (COUNTRY, "/northamerica", "/"):
            with self.subTest(path=path):
                self.assertNotContains(self.client.get(path), "Plan your trip with our concierge")


@override_settings(CONCIERGE_PREVIEW_KEY="open-sesame")
class ChatEndpointTest(SimpleTestCase):
    def post(self, **payload):
        return self.client.post(
            "/concierge/chat", json.dumps(payload), content_type="application/json"
        )

    def test_the_endpoint_is_shut_to_anyone_without_the_cookie(self):
        # Otherwise the toggle would only hide the button, and the model behind
        # it would be free for anyone who knew the URL.
        response = self.post(messages=[{"role": "user", "content": "hello"}])

        self.assertEqual(response.status_code, 404)

    def test_an_unconfigured_server_says_so_rather_than_failing(self):
        unlocked(self)
        with mock.patch.object(agent, "is_configured", return_value=False):
            response = self.post(messages=[{"role": "user", "content": "hello"}])

        self.assertEqual(response.status_code, 503)

    def test_a_reply_carries_the_text_and_the_brief(self):
        unlocked(self)
        brief = {"destination": "Granada", "candidates": []}
        with mock.patch.object(agent, "is_configured", return_value=True), \
             mock.patch.object(agent, "reply", return_value=("Two nights, then.", brief)):
            response = self.post(
                messages=[{"role": "user", "content": "Granada in March"}], path="x"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reply"], "Two nights, then.")
        self.assertEqual(response.json()["brief"]["destination"], "Granada")

    def test_an_empty_or_malformed_conversation_is_refused(self):
        unlocked(self)
        with mock.patch.object(agent, "is_configured", return_value=True):
            self.assertEqual(self.post(messages=[]).status_code, 400)
            self.assertEqual(
                self.post(messages=[{"role": "assistant", "content": "hi"}]).status_code, 400
            )

    def test_a_failing_model_call_does_not_leak_its_exception(self):
        unlocked(self)
        with mock.patch.object(agent, "is_configured", return_value=True), \
             mock.patch.object(agent, "reply", side_effect=RuntimeError("api key sk-xyz")):
            response = self.post(messages=[{"role": "user", "content": "hi"}])

        self.assertEqual(response.status_code, 502)
        self.assertNotIn("sk-xyz", response.content.decode())


class RateLimitBucketTest(SimpleTestCase):
    def test_forwarded_for_does_not_choose_the_bucket(self):
        # A client picks its own X-Forwarded-For, so trusting it would let one
        # caller spread its turns over as many buckets as it likes.
        request = RequestFactory().post(
            "/concierge/chat", HTTP_X_FORWARDED_FOR="9.9.9.9", REMOTE_ADDR="10.0.0.1"
        )

        self.assertEqual(views._client_ip(request), "10.0.0.1")


class AgentToolTest(SimpleTestCase):
    def test_a_path_cannot_climb_out_of_the_content_tree(self):
        self.assertEqual(agent._clean_path("../../etc/passwd"), "")
        self.assertEqual(agent._clean_path("/northamerica/nicaragua/"),
                         "northamerica/nicaragua")

    def test_reading_a_real_page_returns_its_text(self):
        data = json.loads(agent.tool_read_page("northamerica/nicaragua/granada"))

        self.assertEqual(data["title"], "Granada")
        self.assertTrue(data["text"])

    def test_reading_a_made_up_page_says_so(self):
        self.assertIn("No such page", agent.tool_read_page("northamerica/atlantis"))

    def test_the_brief_drops_places_that_are_not_in_the_guide(self):
        brief = agent._normalise_brief({
            "destination": "Granada",
            "interests": "walking",
            "candidates": [
                {"title": "Granada", "path": "northamerica/nicaragua/granada", "why": "base"},
                {"title": "Hotel Invented", "path": "northamerica/nicaragua/nowhere"},
            ],
        })

        self.assertEqual([c["path"] for c in brief["candidates"]],
                         ["northamerica/nicaragua/granada"])

    def test_providers_come_back_with_their_published_contacts(self):
        providers = json.loads(agent.tool_list_providers("southamerica/suriname/paramaribo"))

        self.assertTrue(providers)
        for provider in providers:
            self.assertTrue(provider["title"])
            self.assertTrue(provider["path"])
        # The details are the operator's own, as published on their page.
        self.assertTrue(any(p.get("url") or p.get("phone") or p.get("email")
                            for p in providers))

    def test_a_destination_with_no_operators_says_so_rather_than_guessing(self):
        self.assertIn("no bookable operators",
                      agent.tool_list_providers("northamerica/nicaragua/boaco"))
