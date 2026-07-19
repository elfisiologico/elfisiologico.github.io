#!/usr/bin/env python3
"""Build a reproducible inventory of the public BioTypical RSS corpus."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path


ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"

TOPIC_PATTERNS = {
    "biotipos": r"\b(?:biotype|temperament|choleric|phlegmatic|sanguine|melancholic|unani|balanc)",
    "pareja_y_relaciones": r"relationship|dating|marriage|couple|partner|love|sex|breakup|divorce",
    "infancia_y_crianza": r"child|parent|mother|father|mom|dad|kid|family|gentle parenting",
    "sistemica_y_trauma": r"systemic|trauma|belief|loyalty|lineage|psychomagic|therapy|therapist",
    "personalidad_y_emociones": r"personality|emotion|anger|sad|fear|anxiety|depress|ego|identity",
    "trabajo_y_liderazgo": r"work|business|career|job|leader|team|entrepreneur|advertis|money",
    "cuerpo_y_salud": r"body|health|food|diet|sleep|disease|medical|biology|genetic|brain",
    "genero_y_cultura": r"masculin|feminin|\bmen\b|\bwomen\b|culture|generation|social|politic",
}

BOILERPLATE_MARKERS = (
    "Confused about BioTypes?",
    "For more information on BioTypes",
    "Hosted by Rodrigo",
    "FOLLOW US ON SOCIALS",
    "Support the show",
)


def clean_html(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value or "", flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def duration_hms(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def webpage_from_audio(audio_url: str) -> str:
    match = re.search(r"/episodes/(.+?)\.mp3(?:\?|$)", audio_url)
    if not match:
        return ""
    return f"https://biotypical.buzzsprout.com/1372156/episodes/{match.group(1)}"


def classify(title: str, description: str) -> list[str]:
    substantive = description
    marker_positions = [substantive.find(marker) for marker in BOILERPLATE_MARKERS]
    marker_positions = [position for position in marker_positions if position >= 0]
    if marker_positions:
        substantive = substantive[: min(marker_positions)]
    haystack = f"{title} {substantive}".lower()
    return [name for name, pattern in TOPIC_PATTERNS.items() if re.search(pattern, haystack)]


def parse_feed(source: Path) -> list[dict[str, object]]:
    root = ET.parse(source).getroot()
    records: list[dict[str, object]] = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        description = clean_html(item.findtext("description") or "")
        enclosure = item.find("enclosure")
        audio_url = enclosure.attrib.get("url", "") if enclosure is not None else ""
        raw_duration = item.findtext(f"{{{ITUNES}}}duration") or "0"
        try:
            seconds = int(raw_duration)
        except ValueError:
            parts = [int(part) for part in raw_duration.split(":")]
            seconds = sum(part * 60**index for index, part in enumerate(reversed(parts)))
        raw_date = item.findtext("pubDate") or ""
        try:
            published = datetime.strptime(raw_date, "%a, %d %b %Y %H:%M:%S %z").date().isoformat()
        except ValueError:
            published = raw_date
        number_match = re.match(r"^(\d+)\.\s*", title)
        records.append(
            {
                "episode_number": int(number_match.group(1)) if number_match else None,
                "title": title,
                "published_at": published,
                "duration_seconds": seconds,
                "duration_hms": duration_hms(seconds),
                "topics_preliminary": classify(title, description),
                "description": description,
                "webpage_url": webpage_from_audio(audio_url),
                "audio_url": audio_url,
                "transcript_status": "pending_audit",
                "review_status": "not_reviewed",
            }
        )
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rss", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("output_csv", type=Path)
    args = parser.parse_args()

    records = parse_feed(args.rss)
    args.output_json.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with args.output_csv.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = list(records[0]) if records else []
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = dict(record)
            row["topics_preliminary"] = "|".join(record["topics_preliminary"])
            writer.writerow(row)

    total_seconds = sum(int(record["duration_seconds"]) for record in records)
    print(
        f"Generated {len(records)} records; total audio "
        f"{duration_hms(total_seconds)} ({total_seconds / 3600:.1f} h)."
    )


if __name__ == "__main__":
    main()
