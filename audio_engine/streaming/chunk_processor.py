"""
ChunkProcessor: process a time window using parallel track workers.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

from pydub import AudioSegment

from audio_engine.renderer.clip_processor import ClipProcessor
from audio_engine.streaming.clip_scheduler import ClipScheduler, ClipSlice
from audio_engine.utils.logger import get_logger

logger = get_logger(__name__)


class ChunkProcessor:
    """
    Process a single chunk window with parallel per-track workers.
    """

    def __init__(
        self,
        clip_processor: Optional[ClipProcessor] = None,
        max_workers: int = 4,
        sample_rate: Optional[int] = None,
        channels: Optional[int] = None,
        sample_width: Optional[int] = None,
    ):
        self.clip_processor = clip_processor or ClipProcessor()
        self.max_workers = max_workers
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = sample_width

    def process_chunk(
        self,
        clip_scheduler: ClipScheduler,
        chunk_start: float,
        chunk_end: float,
        role_ranges: Optional[Dict[str, List]] = None,
        default_ducking: Optional[Dict] = None,
        default_compression: Optional[Dict] = None,
    ) -> AudioSegment:
        """
        Process all tracks within a time chunk and return mixed AudioSegment.
        """
        chunk_duration = max(0.0, chunk_end - chunk_start)
        chunk_ms = int(chunk_duration * 1000)
        if chunk_ms <= 0:
            return AudioSegment.silent(duration=0)

        active = clip_scheduler.get_active_clips(chunk_start, chunk_end)
        tracks = {track.get("id", "unknown"): track for track in clip_scheduler.tracks}

        def process_track(track_id: str, slices: List[ClipSlice]) -> AudioSegment:
            track = tracks.get(track_id, {})
            track_gain = track.get("gain", 0.0)
            track_role = track.get("role")
            track_semantic_role = track.get("semantic_role")
            track_eq_preset = track.get("eq_preset")

            buffer = AudioSegment.silent(duration=chunk_ms, frame_rate=self.sample_rate or 44100)
            if self.channels and buffer.channels != self.channels:
                buffer = buffer.set_channels(self.channels)
            if self.sample_width and buffer.sample_width != self.sample_width:
                buffer = buffer.set_sample_width(self.sample_width)
            for clip_slice in slices:
                try:
                    audio = AudioSegment.from_file(
                        clip_slice.file_path,
                        start_second=clip_slice.source_start_sec,
                        duration=clip_slice.duration_sec,
                    )
                    if self.sample_rate and audio.frame_rate != self.sample_rate:
                        audio = audio.set_frame_rate(self.sample_rate)
                    if self.channels and audio.channels != self.channels:
                        audio = audio.set_channels(self.channels)
                    if self.sample_width and audio.sample_width != self.sample_width:
                        audio = audio.set_sample_width(self.sample_width)

                    clip_copy = dict(clip_slice.clip)
                    clip_copy["_audio_override"] = audio
                    clip_copy["_timeline_start"] = clip_slice.output_start_sec
                    clip_copy["_overlay_start"] = clip_slice.output_start_sec - chunk_start

                    buffer = self.clip_processor.process_clip(
                        canvas=buffer,
                        clip=clip_copy,
                        track_gain=track_gain,
                        project_duration=clip_scheduler.project_duration,
                        role_ranges=role_ranges,
                        track_role=track_role,
                        default_ducking=default_ducking,
                        default_compression=default_compression,
                        track_semantic_role=track_semantic_role,
                        track_eq_preset=track_eq_preset,
                    )
                except Exception as exc:
                    logger.warning(f"Failed to process clip slice in track {track_id}: {exc}")
                    continue

            if track_role != "sfx":
                try:
                    from audio_engine.dsp.balance import apply_role_loudness
                    buffer = apply_role_loudness(buffer, track_role)
                except Exception as exc:
                    logger.warning(f"Failed to apply role loudness for track {track_id}: {exc}")

            return buffer

        # Stage 1: parallel track processing
        track_buffers: Dict[str, AudioSegment] = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(process_track, track_id, slices): track_id
                for track_id, slices in active.items()
            }
            for future in futures:
                track_id = futures[future]
                track_buffers[track_id] = future.result()

        # Stage 2: bus mixing (controlled)
        mixed = AudioSegment.silent(duration=chunk_ms, frame_rate=self.sample_rate or 44100)
        if self.channels and mixed.channels != self.channels:
            mixed = mixed.set_channels(self.channels)
        if self.sample_width and mixed.sample_width != self.sample_width:
            mixed = mixed.set_sample_width(self.sample_width)
        for track_id in sorted(track_buffers.keys()):
            try:
                mixed = mixed.overlay(track_buffers[track_id])
            except Exception as exc:
                logger.warning(f"Failed to mix track {track_id}: {exc}")

        return mixed
