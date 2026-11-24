"""Send the itinerary by email."""
import httpx

EMAIL_URL = "https://api.mailer.example/v1/send"


def send_itinerary(ctx, to, body):
    r = httpx.post(EMAIL_URL, json={"to": to, "html": body})
    return r.status_code
