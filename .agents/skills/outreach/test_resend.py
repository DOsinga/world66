import sys
import tempfile
import unittest
import zipfile
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import resend


class GmailMailedTest(unittest.TestCase):
    def test_reads_recipients_and_replies(self):
        sent = EmailMessage()
        sent["From"] = "Richard <richard@world66.ai>"
        sent["To"] = "Provider <provider@example.com>"

        reply = EmailMessage()
        reply["From"] = "Reply <reply@example.com>"
        reply["To"] = "Richard <richard@world66.ai>"

        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "mail.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("sent.eml", sent.as_bytes())
                zf.writestr("reply.eml", reply.as_bytes())

            self.assertEqual(
                resend.gmail_mailed(directory),
                {"provider@example.com", "reply@example.com"},
            )

    def test_missing_export_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(SystemExit, "No Gmail export found"):
                resend.gmail_mailed(directory)


class InboxTest(unittest.TestCase):
    @patch.object(resend, "get")
    def test_reads_every_page(self, get):
        get.side_effect = [
            {"data": [{"id": "newer"}], "has_more": True},
            {"data": [{"id": "older"}], "has_more": False},
        ]

        self.assertEqual(resend.inbox(), [{"id": "newer"}, {"id": "older"}])
        self.assertEqual(
            [call.args[0] for call in get.call_args_list],
            [
                "https://api.resend.com/emails/receiving?limit=100",
                "https://api.resend.com/emails/receiving?limit=100&after=newer",
            ],
        )


if __name__ == "__main__":
    unittest.main()
