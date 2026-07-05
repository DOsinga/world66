#!/usr/bin/env python3
"""
Batch-generate audio-guide MP3s from POI markdown using Google Cloud Text-to-Speech.

This is the production path (swaps in over the macOS `say` placeholders used in the
POC — same output filenames). It is a *build-time* job: run it once per POI, commit
or serve the MP3s statically. No live TTS call happens in the app.

One-time setup (interactive — run these yourself with the `!` prefix):
    ! gcloud auth application-default login
    ! gcloud config set project YOUR_PROJECT_ID
    ! gcloud services enable texttospeech.googleapis.com

Then:
    python3 generate_audio_google.py            # generate for the POC's 10 POIs
    python3 generate_audio_google.py --glob 'content/europe/france/cotedazur/marseille/*.md'

Cost: Neural2 voices are ~$16 / 1M characters; a ~200-word story is ~1.2k chars, so a
673-POI city is ~$13 one-time (and often free under the 1M-char/month free tier).
Only changed stories are re-synthesized (text is hashed in .audio_hashes.json).
"""
import argparse, base64, glob, hashlib, json, os, subprocess, sys, urllib.request, urllib.error
from pathlib import Path

import frontmatter  # pip install python-frontmatter

TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"


def access_token() -> str:
    try:
        return subprocess.run(
            ["gcloud", "auth", "application-default", "print-access-token"],
            capture_output=True, text=True, check=True).stdout.strip()
    except subprocess.CalledProcessError:
        sys.exit("No ADC token. Run: gcloud auth application-default login")


def project_id() -> str:
    pid = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if pid:
        return pid
    pid = subprocess.run(["gcloud", "config", "get-value", "project"],
                         capture_output=True, text=True).stdout.strip()
    if not pid or pid == "(unset)":
        sys.exit("No project set. Run: gcloud config set project YOUR_PROJECT_ID")
    return pid


def synthesize(text: str, token: str, project: str, voice: str, lang: str) -> bytes:
    body = json.dumps({
        "input": {"text": text},
        "voice": {"languageCode": lang, "name": voice},
        "audioConfig": {"audioEncoding": "MP3", "speakingRate": 0.98},
    }).encode()
    req = urllib.request.Request(TTS_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {token}",
        "x-goog-user-project": project,
        "Content-Type": "application/json; charset=utf-8",
    })
    try:
        resp = urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        sys.exit(f"TTS API error {e.code}: {e.read().decode()[:400]}")
    return base64.b64decode(json.loads(resp.read())["audioContent"])


def narration(md_path: Path) -> tuple[str, str]:
    post = frontmatter.load(md_path)
    title = post.metadata.get("title", md_path.stem)
    body = (post.content or "").strip()
    return md_path.stem, f"{title}. {body}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--glob", help="glob of POI .md files (default: the POC's tour_data.json slugs)")
    ap.add_argument("--out", default="audio", help="output dir (default: audio/)")
    ap.add_argument("--voice", default="en-US-Neural2-D", help="Google TTS voice name")
    ap.add_argument("--lang", default="en-US")
    ap.add_argument("--content-root", default=".", help="repo root for resolving tour_data slugs")
    args = ap.parse_args()

    if args.glob:
        files = [Path(p) for p in glob.glob(args.glob)]
    else:
        tour = json.loads(Path("tour_data.json").read_text())
        root = Path(args.content_root)
        files = [root / "content/europe/france/cotedazur/marseille" / f"{p['slug']}.md"
                 for p in tour]

    out = Path(args.out); out.mkdir(exist_ok=True)
    hpath = out / ".audio_hashes.json"
    hashes = json.loads(hpath.read_text()) if hpath.exists() else {}
    token, project = access_token(), project_id()

    made = skipped = 0
    for f in files:
        if not f.exists():
            print("  missing:", f); continue
        slug, text = narration(f)
        digest = hashlib.sha256((args.voice + "\n" + text).encode()).hexdigest()
        mp3 = out / f"{slug}.mp3"
        if mp3.exists() and hashes.get(slug) == digest:
            skipped += 1; continue
        mp3.write_bytes(synthesize(text, token, project, args.voice, args.lang))
        hashes[slug] = digest
        made += 1
        print(f"  ✓ {slug}.mp3 ({len(text)} chars)")

    hpath.write_text(json.dumps(hashes, indent=2))
    print(f"\nDone. {made} generated, {skipped} unchanged. Voice={args.voice}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
