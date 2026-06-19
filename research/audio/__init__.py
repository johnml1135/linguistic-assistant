"""Optional audio evidence add-on for the Swahili/Indonesian/Tagalog/Spanish research data."""

from .catalog import load_audio_catalog
from .samples import load_sample_manifest, resolve_and_persist_samples

__all__ = [
    "load_audio_catalog",
    "load_sample_manifest",
    "resolve_and_persist_samples",
]