from __future__ import annotations

import asyncio
import os
import re
import shutil
from pathlib import Path

import render_episode_hq as hq


def render_image_segment_smooth(asset: hq.RenderAsset, seconds: float, out: Path, motion_index: int) -> None:
    """Jitter-free 4K Ken Burns motion for still images."""
    frames = max(2, int(round(seconds * hq.FPS)))
    denom = max(1, frames - 1)
    t = f"(on/{denom})"
    smooth = f"(3*{t}*{t}-2*{t}*{t}*{t})"

    if motion_index % 2 == 0:
        zoom = f"1.0+0.04*{smooth}"
        motion = "zoom_in_smooth"
    else:
        zoom = f"1.04-0.04*{smooth}"
        motion = "zoom_out_smooth"

    super_w = hq.OUTPUT_W * 4
    super_h = hq.OUTPUT_H * 4
    vf = (
        f"scale={super_w}:{super_h}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={super_w}:{super_h},"
        f"zoompan=z='{zoom}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':"
        f"d={frames}:s={hq.OUTPUT_W}x{hq.OUTPUT_H}:fps={hq.FPS},"
        "format=yuv420p"
    )

    hq.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-loop", "1", "-i", str(asset.path),
        "-vf", vf,
        "-frames:v", str(frames),
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-r", str(hq.FPS), "-pix_fmt", "yuv420p", str(out),
    ])
    out.with_suffix(".motion").write_text(motion, encoding="utf-8")


def _split_tts_chunks(script: str, max_chars: int = 2400) -> list[str]:
    text = re.sub(r"\s+", " ", script).strip()
    if not text:
        raise RuntimeError("TTS script is empty")

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) > max_chars:
            words = sentence.split()
            piece = ""
            for word in words:
                candidate = f"{piece} {word}".strip()
                if piece and len(candidate) > max_chars:
                    chunks.append(piece)
                    piece = word
                else:
                    piece = candidate
            if piece:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.append(piece)
            continue

        candidate = f"{current} {sentence}".strip()
        if current and len(candidate) > max_chars:
            chunks.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


async def make_tts_resilient(script: str, out: Path) -> None:
    """Chunked Edge TTS with retries and voice fallback.

    Long single requests can intermittently return NoAudioReceived. Splitting narration
    into smaller requests prevents one transient Edge TTS failure from killing a full
    render, and each chunk is retried with alternate English voices before failing.
    """
    chunks = _split_tts_chunks(script)
    tmp = out.parent / f".{out.stem}-tts-parts"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True, exist_ok=True)

    preferred = os.getenv("TTS_VOICE", "en-US-AndrewNeural")
    voices: list[str] = []
    for voice in (preferred, "en-US-AndrewNeural", "en-US-GuyNeural", "en-US-BrianNeural"):
        if voice and voice not in voices:
            voices.append(voice)
    rate = os.getenv("TTS_RATE", "-4%")

    parts: list[Path] = []
    try:
        for index, chunk in enumerate(chunks, 1):
            part = tmp / f"part_{index:03d}.mp3"
            last_error: Exception | None = None
            success = False
            for attempt in range(6):
                voice = voices[min(attempt // 2, len(voices) - 1)]
                try:
                    if part.exists():
                        part.unlink()
                    communicate = hq.edge_tts.Communicate(chunk, voice=voice, rate=rate)
                    await communicate.save(str(part))
                    if not part.is_file() or part.stat().st_size < 1500:
                        raise RuntimeError("TTS returned an empty/undersized audio chunk")
                    if hq.duration(part) <= 0.2:
                        raise RuntimeError("TTS returned a zero-duration audio chunk")
                    success = True
                    break
                except Exception as exc:
                    last_error = exc
                    if part.exists():
                        part.unlink()
                    await asyncio.sleep(min(8, 1 + attempt * 2))
            if not success:
                raise RuntimeError(f"TTS failed for chunk {index}/{len(chunks)} after retries: {last_error}")
            parts.append(part)

        concat = tmp / "concat.txt"
        concat.write_text("\n".join(f"file '{p.as_posix()}'" for p in parts) + "\n", encoding="utf-8")
        hq.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat),
            "-c:a", "libmp3lame", "-b:a", "192k", str(out),
        ])
        if not out.is_file() or out.stat().st_size < 10_000 or hq.duration(out) < 30:
            raise RuntimeError("Final narration validation failed after TTS concatenation")
    finally:
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)


def main() -> None:
    hq.render_image_segment = render_image_segment_smooth
    hq.make_tts = make_tts_resilient
    hq.main()


if __name__ == "__main__":
    main()
