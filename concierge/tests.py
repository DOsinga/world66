import json
import tempfile
from pathlib import Path
from unittest import mock

from django.test import RequestFactory, SimpleTestCase, override_settings

from concierge import agent, mail, outreach, views
from concierge.preview import COOKIE_NAME, make_token
from guide.models import load_page

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
        self.assertNotContains(response, "Plan &amp; book")

    def test_a_previewer_sees_it(self):
        unlocked(self)

        response = self.client.get(CITY)

        self.assertContains(response, "Plan &amp; book")
        self.assertContains(response, "concierge.js")

    def test_a_forged_cookie_does_not_unlock_it(self):
        self.client.cookies[COOKIE_NAME] = "on"

        self.assertNotContains(self.client.get(CITY), "Plan &amp; book")


@override_settings(CONCIERGE_PREVIEW_KEY="open-sesame")
class WhereTheButtonAppearsTest(SimpleTestCase):
    def setUp(self):
        unlocked(self)

    def test_it_is_on_destinations_poi_lists_and_pois(self):
        for path in (CITY,
                     CITY + "/eating_out",
                     "/northamerica/nicaragua/isla_ometepe"):
            with self.subTest(path=path):
                self.assertContains(self.client.get(path), "Plan &amp; book")

    def test_it_is_not_on_countries_continents_or_the_home_page(self):
        for path in (COUNTRY, "/northamerica", "/"):
            with self.subTest(path=path):
                self.assertNotContains(self.client.get(path), "Plan &amp; book")


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
             mock.patch.object(agent, "reply",
                               return_value=("Two nights, then.", {"brief": brief})):
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


PROVIDER = "southamerica/suriname/paramaribo/cardy_adventures"
OTHER_PROVIDER = "southamerica/suriname/paramaribo/all_suriname_tours"
TRAVELLER = {"name": "Sam", "email": "sam@example.com"}


def a_draft(providers=(PROVIDER,)):
    return {
        "subject": "Upper Suriname River, 12-15 July, two people",
        "message": "Two of us, 12 to 15 July, hoping for two nights at a river lodge.",
        "providers": list(providers),
    }


class ResolveProvidersTest(SimpleTestCase):
    def test_it_keeps_operators_that_publish_an_address(self):
        keep, dropped = outreach.resolve_providers([PROVIDER])

        self.assertEqual([p.path for p in keep], [PROVIDER])
        self.assertEqual(dropped, [])

    def test_a_path_the_model_made_up_never_becomes_a_recipient(self):
        keep, dropped = outreach.resolve_providers(
            ["southamerica/suriname/paramaribo/invented_tours", "../../etc/passwd"]
        )

        self.assertEqual(keep, [])
        self.assertIn("not an operator", " ".join(dropped))

    def test_an_editorial_page_is_not_an_operator(self):
        keep, _ = outreach.resolve_providers(["southamerica/suriname/paramaribo"])

        self.assertEqual(keep, [])

    def test_it_never_returns_more_than_the_cap(self):
        keep, _ = outreach.resolve_providers([PROVIDER, OTHER_PROVIDER] * 8)

        self.assertLessEqual(len(keep), outreach.MAX_PROVIDERS)

    def test_an_operator_that_asked_to_be_left_alone_is_dropped(self):
        page = load_page(PROVIDER)
        page.meta["no_enquiries"] = True

        self.assertFalse(outreach.accepts_enquiries(page))

    def test_the_recipient_address_comes_from_the_page(self):
        page = load_page(PROVIDER)

        self.assertEqual(outreach.provider_email(page), page.meta["email"])


class DraftSigningTest(SimpleTestCase):
    def test_an_edited_draft_no_longer_verifies(self):
        token = outreach.sign_draft(a_draft())
        tampered = token[:-4] + "aaaa"

        self.assertIsNotNone(outreach.load_draft(token))
        self.assertIsNone(outreach.load_draft(tampered))

    def test_the_agent_signs_only_operators_it_could_resolve(self):
        card, message = agent._build_draft({
            "providers": [PROVIDER, "southamerica/suriname/paramaribo/invented_tours"],
            "subject": "Hello",
            "message": "Two of us in July.",
        })

        self.assertEqual([p["path"] for p in card["providers"]], [PROVIDER])
        self.assertIn("Left out", message)
        self.assertEqual(outreach.load_draft(card["token"])["providers"], [PROVIDER])

    def test_no_draft_at_all_when_nobody_can_be_reached(self):
        card, message = agent._build_draft({
            "providers": ["southamerica/suriname/paramaribo"],
            "subject": "Hello",
            "message": "Two of us in July.",
        })

        self.assertIsNone(card)
        self.assertIn("Nothing to send", message)


class EnvelopeTest(SimpleTestCase):
    def test_the_operator_is_told_why_they_are_hearing_from_us(self):
        provider = load_page(PROVIDER)
        subject, body = outreach.build_enquiry(
            provider, a_draft(), TRAVELLER,
            "https://world66.ai/" + PROVIDER, "https://world66.ai/concierge/no-enquiries/x",
        )

        self.assertIn("12-15 July", subject)
        self.assertIn("found you on World66", body)
        self.assertIn("no commission", body)
        self.assertIn("No more enquiries like this", body)
        self.assertIn(TRAVELLER["email"], body)

    def test_the_traveller_is_told_nothing_has_gone_out_yet(self):
        subject, body = outreach.build_confirmation(
            a_draft(), [load_page(PROVIDER)], TRAVELLER, "https://world66.ai/concierge/confirm/x"
        )

        self.assertIn("Confirm", subject)
        self.assertIn("Nothing has gone to them yet", body)
        self.assertIn("Cardy Adventures", body)


@override_settings(CONCIERGE_PREVIEW_KEY="open-sesame")
class EnquiryEndpointTest(SimpleTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.dict(
            "os.environ", {"CONCIERGE_LEDGER": str(Path(self.tmp.name) / "enq.jsonl")}
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def post(self, **payload):
        return self.client.post(
            "/concierge/enquiry", json.dumps(payload), content_type="application/json"
        )

    def test_it_is_shut_to_anyone_without_the_preview_cookie(self):
        self.assertEqual(self.post(token="x", name="Sam", email="sam@example.com").status_code, 404)

    def test_an_unverified_address_gets_a_confirmation_and_no_operator_is_written_to(self):
        unlocked(self)
        sent = []
        with mock.patch.object(mail, "is_configured", return_value=True), \
             mock.patch.object(mail, "send", side_effect=lambda *a, **k: sent.append(a) or "id1"):
            response = self.post(
                token=outreach.sign_draft(a_draft()), name="Sam", email="sam@example.com"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0][0], "sam@example.com")

    def test_a_bad_address_is_refused(self):
        unlocked(self)
        with mock.patch.object(mail, "is_configured", return_value=True), \
             mock.patch.object(mail, "send") as send:
            response = self.post(
                token=outreach.sign_draft(a_draft()), name="Sam", email="not-an-address"
            )

        self.assertEqual(response.status_code, 400)
        send.assert_not_called()

    def test_a_filled_honeypot_is_answered_politely_and_sends_nothing(self):
        unlocked(self)
        with mock.patch.object(mail, "is_configured", return_value=True), \
             mock.patch.object(mail, "send") as send:
            response = self.post(
                token=outreach.sign_draft(a_draft()), name="Sam",
                email="sam@example.com", website="http://spam.example",
            )

        self.assertEqual(response.status_code, 200)
        send.assert_not_called()

    def test_a_forged_draft_is_refused(self):
        unlocked(self)
        with mock.patch.object(mail, "is_configured", return_value=True), \
             mock.patch.object(mail, "send") as send:
            response = self.post(token="not-a-token", name="Sam", email="sam@example.com")

        self.assertEqual(response.status_code, 400)
        send.assert_not_called()


class ConfirmAndSendTest(SimpleTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ledger = Path(self.tmp.name) / "enq.jsonl"
        patcher = mock.patch.dict("os.environ", {"CONCIERGE_LEDGER": str(self.ledger)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.token = outreach.sign_confirmation(
            {"draft": a_draft(), "traveller": TRAVELLER}
        )

    def test_opening_the_link_sends_nothing(self):
        # Mail clients and spam filters fetch links on their own; a GET that
        # sent the enquiry would put it out without anybody deciding to.
        with mock.patch.object(mail, "is_configured", return_value=True), \
             mock.patch.object(mail, "send") as send:
            response = self.client.get(f"/concierge/confirm/{self.token}")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Send this enquiry?")
        send.assert_not_called()

    def test_the_button_sends_it_with_the_traveller_on_the_reply_to(self):
        calls = []
        with mock.patch.object(mail, "is_configured", return_value=True), \
             mock.patch.object(mail, "send",
                               side_effect=lambda *a, **k: calls.append((a, k)) or "id1"):
            response = self.client.post(f"/concierge/confirm/{self.token}")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cardy Adventures")
        (to, subject, body), kwargs = calls[0]
        self.assertEqual(to, load_page(PROVIDER).meta["email"])
        self.assertEqual(kwargs["reply_to"], TRAVELLER["email"])
        self.assertIn("no-enquiries", body)

    def test_the_link_works_once(self):
        with mock.patch.object(mail, "is_configured", return_value=True), \
             mock.patch.object(mail, "send", return_value="id1") as send:
            self.client.post(f"/concierge/confirm/{self.token}")
            self.assertEqual(send.call_count, 1)
            response = self.client.post(f"/concierge/confirm/{self.token}")

        self.assertEqual(send.call_count, 1)
        self.assertContains(response, "Already sent")

    def test_every_send_lands_in_the_ledger(self):
        with mock.patch.object(mail, "is_configured", return_value=True), \
             mock.patch.object(mail, "send", return_value="id1"):
            self.client.post(f"/concierge/confirm/{self.token}")

        rows = [json.loads(line) for line in self.ledger.read_text().splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["provider_path"], PROVIDER)
        self.assertEqual(rows[0]["message_id"], "id1")

    def test_an_expired_link_sends_nothing(self):
        with mock.patch.object(mail, "is_configured", return_value=True), \
             mock.patch.object(mail, "send") as send:
            response = self.client.post("/concierge/confirm/rubbish")

        self.assertEqual(response.status_code, 400)
        send.assert_not_called()

    def test_an_operator_who_opted_out_after_signing_is_still_dropped(self):
        # The signed token names paths, not addresses, so the check happens
        # against the page as it is at send time.
        page = load_page(PROVIDER)
        page.meta["no_enquiries"] = True
        with mock.patch.object(mail, "is_configured", return_value=True), \
             mock.patch.object(mail, "send") as send, \
             mock.patch("concierge.outreach.load_page", return_value=page):
            response = self.client.post(f"/concierge/confirm/{self.token}")

        self.assertEqual(response.status_code, 400)
        send.assert_not_called()
