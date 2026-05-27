import uuid
from django.db import models


class NegotiationSession(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("contacting", "Contacting"),
        ("negotiating", "Negotiating"),
        ("pending_confirmation", "Offer Pending"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
        ("failed", "Failed"),
    ]

    TERMINAL_STATUSES = {"confirmed", "cancelled", "failed"}

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider_path = models.CharField(max_length=500)
    provider_name = models.CharField(max_length=200)
    provider_whatsapp = models.CharField(max_length=50, blank=True)
    user_name = models.CharField(max_length=200)
    user_email = models.EmailField(blank=True)
    user_whatsapp = models.CharField(max_length=50, blank=True)
    prefs = models.JSONField(default=dict)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default="pending")
    proposed_offer = models.JSONField(default=dict, blank=True)
    group_id = models.UUIDField(null=True, blank=True, db_index=True)
    summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.provider_name} — {self.status}"


class Message(models.Model):
    DIRECTION_CHOICES = [
        ("outbound", "Outbound"),
        ("inbound", "Inbound"),
    ]

    session = models.ForeignKey(
        NegotiationSession, on_delete=models.CASCADE, related_name="messages"
    )
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    body = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    twilio_sid = models.CharField(max_length=100, blank=True, unique=True, null=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"[{self.direction}] {self.body[:60]}"
