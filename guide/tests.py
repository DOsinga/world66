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


class TipMailtoTest(SimpleTestCase):
    @override_settings(TIPS_EMAIL="local-tips@example.com")
    def test_tip_link_appears_on_a_city_but_not_a_country(self):
        city = self.client.get("/europe/france/paris")
        country = self.client.get("/europe/france")

        self.assertEqual(city.status_code, 200)
        self.assertTrue(
            city.context["tip_mailto"].startswith("mailto:local-tips@example.com?")
        )
        self.assertIn(
            "https%3A%2F%2Fworld66.ai%2Feurope%2Ffrance%2Fparis",
            city.context["tip_mailto"],
        )
        self.assertEqual(country.status_code, 200)
        self.assertEqual(country.context["tip_mailto"], "")
