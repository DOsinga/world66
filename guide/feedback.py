"""Visitor feedback endpoint — creates GitHub Issues for review."""
import os
from datetime import datetime, timezone

import httpx
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_POST

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GITHUB_REPO = os.environ.get('GITHUB_REPO', 'DOsinga/world66')
GITHUB_API = 'https://api.github.com'


@require_POST
def submit_feedback(request):
    """Accept visitor feedback and create a GitHub Issue."""
    # Honeypot check — bots fill hidden fields
    if request.POST.get('website', ''):
        return JsonResponse({'status': 'ok'})

    # Rate limiting: 5 per IP per hour
    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
    ip = ip.split(',')[0].strip()
    cache_key = f'feedback_rate_{ip}'
    count = cache.get(cache_key, 0)
    if count >= 5:
        return JsonResponse({'error': 'Too many submissions. Please try again later.'}, status=429)

    text = request.POST.get('feedback', '').strip()
    page_path = request.POST.get('page_path', '').strip()

    if not text or not page_path:
        return JsonResponse({'error': 'Feedback text and page are required.'}, status=400)

    if len(text) > 2000:
        return JsonResponse({'error': 'Feedback too long (max 2000 characters).'}, status=400)

    now = datetime.now(timezone.utc)
    body = f'**Page:** `{page_path}`\n**Submitted:** {now.isoformat()}\n\n---\n\n{text}'

    try:
        resp = httpx.post(
            f'{GITHUB_API}/repos/{GITHUB_REPO}/issues',
            headers={
                'Authorization': f'token {GITHUB_TOKEN}',
                'Accept': 'application/vnd.github.v3+json',
            },
            json={
                'title': f'Feedback: {page_path}',
                'body': body,
                'labels': ['feedback'],
            },
            timeout=10.0,
        )
    except httpx.HTTPError:
        return JsonResponse({'error': 'Something went wrong, please try again later.'}, status=502)

    if resp.status_code in (200, 201):
        cache.set(cache_key, count + 1, timeout=3600)
        return JsonResponse({'status': 'ok'})
    else:
        return JsonResponse({'error': 'Something went wrong, please try again later.'}, status=502)
