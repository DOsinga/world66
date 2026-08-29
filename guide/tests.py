from django.test import SimpleTestCase


class DestinationPoiAggregationTest(SimpleTestCase):
    def test_opted_in_destination_section_lists_flat_pois(self):
        response = self.client.get(
            "/northamerica/netherlandsantilles/bonaire/things_to_do"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bonaire National Marine Park")
        self.assertContains(response, "1000 Steps")
        self.assertContains(response, "Cadushy Distillery")
