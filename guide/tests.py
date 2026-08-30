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
