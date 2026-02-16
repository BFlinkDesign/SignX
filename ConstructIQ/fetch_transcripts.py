"""
Fetch transcripts for all ConstructIQ videos.
Run this on a non-corporate network (phone hotspot, VPN, etc.)

Usage:
    python fetch_transcripts.py

It will update each existing .md file with the transcript,
and regenerate index.md with transcript status.
"""
import json
import re
import time
import xml.etree.ElementTree as ET
from html import unescape
from pathlib import Path

import requests

OUT_DIR = Path(__file__).parent
VIDEOS_JSON = OUT_DIR / "videos.json"


def get_caption_url(session: requests.Session, video_id: str) -> str | None:
    resp = session.get(f"https://www.youtube.com/watch?v={video_id}", timeout=15)
    if resp.status_code != 200:
        return None
    match = re.search(r'"captionTracks":\s*(\[.*?\])', resp.text)
    if not match:
        return None
    raw = match.group(1).encode().decode("unicode_escape")
    tracks = json.loads(raw)
    for track in tracks:
        if track.get("languageCode", "").startswith("en"):
            return track["baseUrl"]
    return tracks[0]["baseUrl"] if tracks else None


def fetch_transcript_text(session: requests.Session, caption_url: str) -> str:
    resp = session.get(caption_url, timeout=15)
    if resp.status_code != 200:
        return ""
    lines = []
    try:
        root = ET.fromstring(resp.text)
        for elem in root.iter():
            if elem.text and elem.tag in ("text", "s", "p"):
                clean = unescape(elem.text.strip())
                if clean and clean != "\n":
                    lines.append(clean)
    except ET.ParseError:
        raw_lines = re.findall(r">([^<]+)<", resp.text)
        for line in raw_lines:
            clean = unescape(line.strip())
            if clean and clean != "\n":
                lines.append(clean)
    return "\n\n".join(lines)


def sanitize_filename(title: str) -> str:
    s = re.sub(r'[<>:"/\\|?*#]', "", title)
    s = re.sub(r"\s+", "-", s.strip())
    s = re.sub(r"-+", "-", s)
    return s[:80]


def main():
    videos = json.loads(VIDEOS_JSON.read_text(encoding="utf-8"))
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    })

    success = 0
    failed = 0

    for i, v in enumerate(videos):
        vid = v["id"]
        title = v["title"]
        fname = sanitize_filename(title)
        filepath = OUT_DIR / f"{fname}.md"

        print(f"[{i+1}/{len(videos)}] {title}...", end=" ", flush=True)

        transcript_text = ""
        try:
            url = get_caption_url(session, vid)
            if url:
                transcript_text = fetch_transcript_text(session, url)
        except Exception as e:
            print(f"ERROR: {e}")

        if transcript_text.strip():
            # Update the markdown file - replace the placeholder
            if filepath.exists():
                content = filepath.read_text(encoding="utf-8")
                content = content.replace(
                    "*Transcript not yet fetched — run `python fetch_transcripts.py` on a non-corporate network.*",
                    transcript_text,
                )
                filepath.write_text(content, encoding="utf-8")
            success += 1
            print("OK")
        else:
            failed += 1
            print("NO TRANSCRIPT")

        # Update videos.json
        v["has_transcript"] = bool(transcript_text.strip())

        if (i + 1) % 10 == 0:
            time.sleep(2)
        else:
            time.sleep(0.5)

    VIDEOS_JSON.write_text(json.dumps(videos, indent=2, ensure_ascii=False), encoding="utf-8")

    # Regenerate index
    _rebuild_index(videos)
    print(f"\nDone! {success} transcripts fetched, {failed} unavailable.")


def _rebuild_index(videos):
    by_date = sorted(videos, key=lambda x: x["date"], reverse=True)
    by_views = sorted(videos, key=lambda x: x["views"], reverse=True)
    s_count = sum(1 for v in videos if v.get("has_transcript"))
    f_count = len(videos) - s_count

    lines = [
        "# ConstructIQ - Complete Video Index",
        "",
        "**Channel:** [@ConstructIQ](https://www.youtube.com/@ConstructIQ) (Tim Fairley)",
        f"**Videos indexed:** {len(videos)}",
        f"**Transcripts available:** {s_count}",
        f"**Transcripts pending:** {f_count}",
        "**Generated:** 2026-02-15",
        "",
        "---",
        "",
        "## Videos by Date (Newest First)",
        "",
        "| # | Date | Title | Views | Transcript |",
        "|---|------|-------|------:|:----------:|",
    ]
    for i, v in enumerate(by_date, 1):
        icon = "Y" if v.get("has_transcript") else "-"
        fn = sanitize_filename(v["title"])
        link = f"[{v['title']}]({fn}.md)"
        lines.append(f"| {i} | {v['date']} | {link} | {v['views']:,} | {icon} |")

    lines += [
        "", "---", "",
        "## Videos by Views (Most Popular First)",
        "",
        "| # | Views | Title | Date |",
        "|---|------:|-------|------|",
    ]
    for i, v in enumerate(by_views, 1):
        fn = sanitize_filename(v["title"])
        link = f"[{v['title']}]({fn}.md)"
        lines.append(f"| {i} | {v['views']:,} | {link} | {v['date']} |")

    (OUT_DIR / "index.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
