"""Speaker diarization for audio transcripts. Optional: requires pyannote and HF token."""

from pathlib import Path
from typing import Optional


def merge_transcript_with_diarization(
    transcript: str,
    audio_path: str,
    hf_token: Optional[str] = None,
) -> str:
    """
    Merge raw transcript with speaker labels from pyannote diarization.
    Returns speaker-attributed, timestamped transcript. Falls back to raw transcript if unavailable.
    """
    try:
        from pyannote.audio import Pipeline
    except ImportError:
        return transcript

    if not hf_token:
        return transcript

    path = Path(audio_path)
    if not path.exists():
        return transcript

    try:
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token,
        )
        diarization = pipeline(audio_path)

        # Build segments: (start, end, speaker)
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append((turn.start, turn.end, speaker))

        if not segments:
            return transcript

        # Simple merge: we don't have word-level timestamps from Whisper,
        # so we approximate by splitting transcript into chunks by segment count.
        lines = [l.strip() for l in transcript.splitlines() if l.strip()]
        if not lines:
            return transcript

        # Distribute lines across speakers (rough approximation)
        n_segments = len(segments)
        lines_per_seg = max(1, len(lines) // n_segments) if n_segments else len(lines)
        result = []
        line_idx = 0
        for start, end, speaker in segments:
            chunk_lines = lines[line_idx : line_idx + lines_per_seg]
            line_idx += lines_per_seg
            if chunk_lines:
                ts = f"[{start:.1f}s-{end:.1f}s]"
                result.append(f"{speaker} {ts}: {' '.join(chunk_lines)}")
        if line_idx < len(lines):
            start, end, speaker = segments[-1]
            result.append(f"{speaker}: {' '.join(lines[line_idx:])}")
        return "\n".join(result)
    except Exception:
        return transcript
