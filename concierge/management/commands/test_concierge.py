"""
Interactive concierge test — no Twilio needed.

Runs the agent against a fake provider session in your terminal.
After each outbound message you type a reply as the "provider".

Usage:
    python manage.py test_concierge
    python manage.py test_concierge europe/netherlands/amersfoort/amersfoort_city_walk
"""

import uuid
from unittest.mock import patch

from django.core.management.base import BaseCommand

from concierge.agent import _do_run
from concierge.models import Message, NegotiationSession
from guide.models import load_page


DEFAULT_PATH = "europe/netherlands/amersfoort/amersfoort_city_walk"


def _fake_send(to_number, body):
    # Called instead of Twilio; return a fake SID so the Message is saved.
    return f"FAKE-{uuid.uuid4().hex[:8]}"


class Command(BaseCommand):
    help = "Simulate a concierge negotiation in the terminal without Twilio."

    def add_arguments(self, parser):
        parser.add_argument(
            "provider_path",
            nargs="?",
            default=DEFAULT_PATH,
            help="Content path to a bookable POI",
        )
        parser.add_argument("--dates", default="mid-June, flexible")
        parser.add_argument("--group", default="2", dest="group_size")
        parser.add_argument("--target", default="", dest="target_price")
        parser.add_argument("--max", default="", dest="max_price")
        parser.add_argument("--notes", default="")
        parser.add_argument("--name", default="Test User", dest="user_name")

    def handle(self, *args, **options):
        path = options["provider_path"]
        poi = load_page(path)
        if not poi:
            self.stderr.write(self.style.ERROR(f"POI not found: {path}"))
            return

        provider_whatsapp = poi.meta.get("whatsapp", "+0000000000")

        session = NegotiationSession.objects.create(
            provider_path=path,
            provider_name=poi.title,
            provider_whatsapp=provider_whatsapp,
            user_name=options["user_name"],
            prefs={
                "dates": options["dates"],
                "group_size": options["group_size"],
                "listed_price": poi.meta.get("price", ""),
                "target_price": options["target_price"],
                "max_price": options["max_price"],
                "notes": options["notes"],
            },
        )

        self.stdout.write(self.style.SUCCESS(
            f"\nStarting concierge session for: {poi.title}"
        ))
        self.stdout.write(f"Session ID: {session.id}\n")
        self.stdout.write("─" * 60)

        last_seen = 0

        with patch("concierge.agent.send_message", side_effect=_fake_send):
            while session.status not in ("agreed", "failed"):
                _do_run(session.id)
                session.refresh_from_db()

                # Print any new outbound messages
                new_msgs = list(
                    session.messages.order_by("timestamp")[last_seen:]
                )
                last_seen = session.messages.count()

                for msg in new_msgs:
                    arrow = "→ CONCIERGE" if msg.direction == "outbound" else "← PROVIDER"
                    self.stdout.write(f"\n{arrow}:\n  {msg.body}\n")

                if session.status in ("agreed", "failed"):
                    break

                # Prompt for provider reply
                try:
                    reply = input("Provider reply (or 'quit'): ").strip()
                except (EOFError, KeyboardInterrupt):
                    self.stdout.write("\nAborted.")
                    break

                if reply.lower() in ("quit", "q", "exit"):
                    break

                if not reply:
                    continue

                Message.objects.create(
                    session=session,
                    direction="inbound",
                    body=reply,
                    twilio_sid=f"FAKE-IN-{uuid.uuid4().hex[:8]}",
                )
                session.status = "negotiating"
                session.save(update_fields=["status", "updated_at"])

        self.stdout.write("\n" + "─" * 60)
        self.stdout.write(f"Final status: {self.style.SUCCESS(session.status)}")
        if session.summary:
            self.stdout.write(f"Summary: {session.summary}")
        self.stdout.write(f"\nFull transcript at: /concierge/session/{session.id}\n")
