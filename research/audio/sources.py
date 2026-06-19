"""Audio source audit: gate downloads on exact-text-match + music-free + acceptable license.

The audit never downloads. It reads a committed manifest of candidate audio sources for the
current targets and reports which (if any) are download-eligible. A source is eligible only when it
records the *same* translation as the text, is music-free, has an acceptable license, and is
explicitly approved. When nothing qualifies, the audit surfaces the curated alternatives shortlist
(other language + open text + music-free audio combinations) instead of substituting a near-match.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

_SOURCES_DIR = Path(__file__).resolve().parent / "sources"
DEFAULT_MANIFEST = _SOURCES_DIR / "audio_sources.json"
DEFAULT_ALTERNATIVES = _SOURCES_DIR / "alternatives.json"


@dataclass(frozen=True)
class AudioSource:
    target_key: str
    target_id: str
    text_title: str
    text_publication_url: str
    audio_provider: str | None
    audio_url: str | None
    matches_text_translation: bool
    music_free: bool | None
    license: str | None
    approved: bool
    status: str
    evidence: str

    @property
    def download_eligible(self) -> bool:
        """Policy gate (defense in depth): every condition must hold, not just `approved`."""
        return bool(
            self.approved
            and self.matches_text_translation
            and self.music_free is True
            and self.license
            and self.audio_url
        )

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["download_eligible"] = self.download_eligible
        return data


def load_audio_sources(path: str | Path = DEFAULT_MANIFEST) -> list[AudioSource]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = data.get("sources", [])
    if not isinstance(entries, list):
        raise ValueError("audio source manifest 'sources' must be a list")
    out: list[AudioSource] = []
    for raw in entries:
        if not isinstance(raw, dict):
            raise ValueError("audio source entry must be an object")
        out.append(
            AudioSource(
                target_key=str(raw.get("target_key", "")).strip(),
                target_id=str(raw.get("target_id", "")).strip(),
                text_title=str(raw.get("text_title", "")),
                text_publication_url=str(raw.get("text_publication_url", "")),
                audio_provider=_opt(raw.get("audio_provider")),
                audio_url=_opt(raw.get("audio_url")),
                matches_text_translation=bool(raw.get("matches_text_translation", False)),
                music_free=_opt_bool(raw.get("music_free")),
                license=_opt(raw.get("license")),
                approved=bool(raw.get("approved", False)),
                status=str(raw.get("status", "unknown")),
                evidence=str(raw.get("evidence", "")),
            )
        )
    return out


def load_alternatives(path: str | Path = DEFAULT_ALTERNATIVES) -> list[dict[str, object]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    candidates = data.get("candidates", [])
    if not isinstance(candidates, list):
        raise ValueError("alternatives manifest 'candidates' must be a list")
    return [c for c in candidates if isinstance(c, dict)]


def approved_sources(sources: list[AudioSource]) -> list[AudioSource]:
    return [s for s in sources if s.download_eligible]


def audit_audio_sources(
    manifest: str | Path = DEFAULT_MANIFEST,
    alternatives: str | Path = DEFAULT_ALTERNATIVES,
) -> dict[str, object]:
    sources = load_audio_sources(manifest)
    approved = approved_sources(sources)
    alts = [] if approved else load_alternatives(alternatives)
    return {
        "approved_count": len(approved),
        "approved": [s.to_dict() for s in approved],
        "sources": [s.to_dict() for s in sources],
        "alternatives": alts,
    }


def _opt(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _opt_bool(value: object) -> bool | None:
    if value is None:
        return None
    return bool(value)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="path to audio_sources.json")
    ap.add_argument("--alternatives", default=str(DEFAULT_ALTERNATIVES), help="path to alternatives.json")
    ap.add_argument("--json", action="store_true", help="emit the raw audit report as JSON")
    args = ap.parse_args(argv)

    report = audit_audio_sources(args.manifest, args.alternatives)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    approved = report["approved"]
    if approved:
        print(f"Download-eligible audio sources ({len(approved)}):")
        for s in approved:  # type: ignore[assignment]
            print(f"  - {s['target_id']}: {s['audio_provider']} -> {s['audio_url']}")
        return 0

    print("No approved audio source for the current targets (exact-match + music-free + license gate).")
    for s in report["sources"]:  # type: ignore[assignment]
        print(f"  - {s['target_id']}: {s['status']} — {s['evidence']}")
    print("\nSuggested language + bible + audio alternatives (verify license + exact match first):")
    for c in report["alternatives"]:  # type: ignore[assignment]
        text = c.get("text", {})
        audio = c.get("audio", {})
        print(f"  - {c.get('language')} ({c.get('language_code')}), script {c.get('script')}")
        print(f"      text:  {text.get('title')} [{text.get('ebible_id')}] — {text.get('license')}")
        print(f"      audio: {audio.get('provider')} — {audio.get('edition')}")
        print(f"      why:   {c.get('why')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
