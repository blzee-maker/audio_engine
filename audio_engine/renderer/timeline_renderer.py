"""
TimelineRenderer orchestrates the entire rendering pipeline.
"""
import os
from typing import Dict, List, Tuple, Optional
from pydub import AudioSegment

from audio_engine.utils.logger import get_logger, log_performance
from audio_engine.validation import validate_timeline
from audio_engine.scene_preprocessor import preprocess_scenes
from audio_engine.autofix import auto_fix_overlaps
from audio_engine.exceptions import FileError, TimelineError
from audio_engine.config import RenderConfig
from audio_engine.renderer.clip_processor import ClipProcessor
from audio_engine.renderer.track_mixer import TrackMixer
from audio_engine.renderer.master_processor import MasterProcessor
from audio_engine.streaming.clip_scheduler import ClipScheduler
from audio_engine.streaming.chunk_processor import ChunkProcessor
from audio_engine.streaming.stream_writer import StreamWriter
from audio_engine.streaming.loudness import (
    measure_lufs_from_file,
    compute_lufs_gain_db,
    StreamingPeakEstimator,
    compute_peak_gain_db,
)
from audio_engine.dsp.eq import apply_scene_tonal_shaping
from audio_engine.dsp.fade_curves import FadeCurve
from audio_engine.dsp.fades import apply_fade_out

logger = get_logger(__name__)


class TimelineRenderer:
    """Main orchestrator for the audio rendering pipeline."""
    
    def __init__(
        self,
        clip_processor: Optional[ClipProcessor] = None,
        track_mixer: Optional[TrackMixer] = None,
        master_processor: Optional[MasterProcessor] = None
    ):
        """
        Initialize TimelineRenderer with optional component dependencies.
        
        Args:
            clip_processor: Optional ClipProcessor instance (creates default if None)
            track_mixer: Optional TrackMixer instance (creates default if None)
            master_processor: Optional MasterProcessor instance (creates default if None)
        """
        self.clip_processor = clip_processor or ClipProcessor()
        self.track_mixer = track_mixer or TrackMixer(self.clip_processor)
        self.master_processor = master_processor or MasterProcessor()
    
    @staticmethod
    def load_timeline(path: str) -> Dict:
        """Load timeline JSON from file."""
        import json
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Timeline file not found: {path}")
            raise FileError(f"Timeline file not found: {path}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in timeline file {path}: {e}")
            raise FileError(f"Invalid JSON in timeline file {path}: {e}")
        except Exception as e:
            logger.error(f"Failed to load timeline file {path}: {e}")
            raise FileError(f"Failed to load timeline file {path}: {e}")
    
    @staticmethod
    def create_canvas(duration_seconds: float) -> AudioSegment:
        """Create a silent audio canvas of specified duration."""
        return AudioSegment.silent(duration=int(duration_seconds * 1000))
    
    @staticmethod
    def get_role_ranges(tracks: List[Dict]) -> Dict[str, List[Tuple[float, float]]]:
        """
        Extract role ranges from tracks for ducking calculations.
        Supports both mix roles (voice, background, etc.) and SFX semantic roles (sfx:impact, etc.).
        
        Returns:
            Dictionary mapping role names to lists of (start, end) tuples.
            Role names can be mix roles (e.g., "voice") or semantic roles (e.g., "sfx:impact").
        """
        role_ranges: Dict[str, List[Tuple[float, float]]] = {}
        
        for track in tracks:
            role = track.get("role")  # mix_role
            if not role:
                continue
            
            # Get track-level semantic_role (if present)
            track_semantic_role = track.get("semantic_role")
            
            for clip in track.get("clips", []):
                if "file" not in clip or "start" not in clip:
                    logger.warning(f"Skipping clip without file or start time in track role '{role}'")
                    continue
                
                try:
                    start = clip.get("start", 0)
                    audio = AudioSegment.from_file(clip["file"])
                    duration = len(audio) / 1000.0
                    end = start + duration
                    
                    # Add mix role range
                    role_ranges.setdefault(role, []).append((start, end))
                    
                    # If SFX track with semantic role, also add semantic role range
                    if role == "sfx":
                        # Clip-level semantic_role overrides track-level
                        clip_semantic_role = clip.get("semantic_role", track_semantic_role)
                        if clip_semantic_role:
                            semantic_role_key = f"sfx:{clip_semantic_role}"
                            role_ranges.setdefault(semantic_role_key, []).append((start, end))
                            
                except FileNotFoundError:
                    logger.warning(f"Audio file not found for role range calculation: {clip['file']}")
                    continue
                except Exception as e:
                    logger.warning(f"Failed to load audio file for role range: {clip.get('file', 'unknown')}: {e}")
                    continue
        
        return role_ranges
    
    @log_performance
    def render(self, timeline_path: str, output_path: str) -> None:
        """
        Render timeline to output audio file.
        
        Args:
            timeline_path: Path to timeline JSON file
            output_path: Path to output WAV file
        """
        logger.info(f"Starting render: {timeline_path} -> {output_path}")
        
        # Load timeline
        try:
            timeline = self.load_timeline(timeline_path)
            logger.debug("Timeline loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load timeline: {e}")
            raise
        
        # Scene Preprocessing
        try:
            timeline = preprocess_scenes(timeline)
            logger.debug("Scene preprocessing completed")
        except Exception as e:
            logger.error(f"Scene preprocessing failed: {e}")
            raise TimelineError(f"Scene preprocessing failed: {e}")
        
        # Auto-fix overlaps
        settings = timeline.get("settings", {})
        min_gap = settings.get("default_silence", 0.0)
        
        for track in timeline.get("tracks", []):
            try:
                auto_fix_overlaps(track, min_gap=min_gap)
            except Exception as e:
                logger.warning(f"Failed to auto-fix overlaps for track {track.get('id', 'unknown')}: {e}")
        
        # Validate
        warnings = validate_timeline(timeline)
        for w in warnings:
            logger.warning(f"⚠ {w}")
        
        # Debug timeline print
        from audio_engine.utils.debug import debug_print_timeline
        debug_print_timeline(timeline)
        
        # Extract settings
        duration = timeline["project"]["duration"]
        default_ducking = settings.get("ducking")
        default_compression = settings.get("dialogue_compression")

        config = RenderConfig.from_timeline_settings(settings)
        
        # Calculate role ranges for ducking
        role_ranges = None
        if default_ducking and default_ducking.get("enabled"):
            try:
                role_ranges = self.get_role_ranges(timeline["tracks"])
                logger.debug("Role ranges calculated for ducking")
            except Exception as e:
                logger.warning(f"Failed to calculate role ranges, ducking may not work: {e}")
        
        # Create canvas
        canvas = self.create_canvas(duration)
        logger.debug(f"Created canvas of {duration}s duration")
        
        # Process tracks
        for track in timeline["tracks"]:
            try:
                track_buffer = self.track_mixer.process_track(
                    track=track,
                    project_duration=duration,
                    role_ranges=role_ranges,
                    default_ducking=default_ducking,
                    default_compression=default_compression
                )
                # Only overlay if track_buffer is valid
                if track_buffer is not None:
                    try:
                        canvas = canvas.overlay(track_buffer)
                        # Validate overlay returned valid canvas
                        if canvas is None:
                            logger.error(f"Canvas overlay returned None for track '{track.get('id', 'unknown')}'")
                            canvas = self.create_canvas(duration)  # Recreate canvas
                        else:
                            logger.debug(f"Track '{track.get('id', 'unknown')}' mixed into canvas")
                    except Exception as e:
                        logger.error(f"Failed to overlay track '{track.get('id', 'unknown')}': {e}")
                else:
                    logger.warning(f"Skipping overlay for track '{track.get('id', 'unknown')}' due to None track_buffer")
            except Exception as e:
                logger.error(f"Failed to process track '{track.get('id', 'unknown')}': {e}")
                # Ensure canvas remains valid after exception
                if canvas is None:
                    canvas = self.create_canvas(duration)
                # Continue with other tracks
        
        # Validate canvas before scene EQ
        if canvas is None:
            logger.error("Canvas is None before scene EQ, recreating")
            canvas = self.create_canvas(duration)
        
        # Apply scene-level tonal shaping (if configured)
        # This applies to the entire mixed canvas for broad tonal adjustments
        # Limited to tilt, high_shelf, low_shelf for v1 (no narrow parametric bands)
        scene_eq = settings.get("eq", {})
        if scene_eq:
            try:
                canvas = apply_scene_tonal_shaping(canvas, scene_eq)
                if canvas is None:
                    logger.error("apply_scene_tonal_shaping returned None, recreating canvas")
                    canvas = self.create_canvas(duration)
                else:
                    logger.debug(f"Applied scene-level tonal shaping: {scene_eq}")
            except Exception as e:
                logger.warning(f"Failed to apply scene-level tonal shaping: {e}")
                if canvas is None:
                    canvas = self.create_canvas(duration)
        
        # Master processing
        config = RenderConfig.from_timeline_settings(settings)
        try:
            canvas = self.master_processor.process(canvas, config)
            # Validate master processing returned valid canvas
            if canvas is None:
                logger.error("Master processing returned None, recreating canvas")
                canvas = self.create_canvas(duration)
        except Exception as e:
            logger.error(f"Master processing failed: {e}")
            # Ensure canvas remains valid after exception
            if canvas is None:
                canvas = self.create_canvas(duration)
        
        # Export final audio
        try:
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            canvas.export(output_path, format="wav")
            logger.info(f"Audio exported successfully to {output_path}")
        except Exception as e:
            logger.error(f"Failed to export audio to {output_path}: {e}")
            raise FileError(f"Failed to export audio to {output_path}: {e}")

    @log_performance
    def render_streaming(self, timeline_path: str, output_path: str) -> None:
        """
        Render timeline using a chunked streaming pipeline.
        """
        logger.info(f"Starting streaming render: {timeline_path} -> {output_path}")

        timeline = self.load_timeline(timeline_path)
        timeline = preprocess_scenes(timeline)

        settings = timeline.get("settings", {})
        min_gap = settings.get("default_silence", 0.0)
        for track in timeline.get("tracks", []):
            auto_fix_overlaps(track, min_gap=min_gap)

        warnings = validate_timeline(timeline)
        for w in warnings:
            logger.warning(f"⚠ {w}")

        duration = timeline["project"]["duration"]
        default_ducking = settings.get("ducking")
        default_compression = settings.get("dialogue_compression")

        config = RenderConfig.from_timeline_settings(settings)

        role_ranges = None
        if default_ducking and default_ducking.get("enabled"):
            role_ranges = self.get_role_ranges(timeline["tracks"])

        chunk_size_sec = config.chunk_size_sec
        max_workers = config.streaming_max_workers
        two_pass_lufs = config.streaming_two_pass_lufs

        # Output format (use config defaults or streaming overrides)
        sample_rate = config.streaming_sample_rate
        channels = config.streaming_channels
        sample_width = config.streaming_sample_width

        clip_processor = self.clip_processor
        scheduler = ClipScheduler(timeline)
        chunk_processor = ChunkProcessor(
            clip_processor=clip_processor,
            max_workers=max_workers,
            sample_rate=sample_rate,
            channels=channels,
            sample_width=sample_width,
        )

        scene_eq = settings.get("eq", {})
        temp_output = output_path

        def render_pass(
            output_file: str,
            gain_db: float = 0.0,
            estimator=None,
            peak_estimator: Optional[StreamingPeakEstimator] = None,
            peak_gain_db: float = 0.0,
        ) -> None:
            writer = StreamWriter(
                output_path=output_file,
                sample_rate=sample_rate,
                channels=channels,
                sample_width=sample_width,
            )
            writer.open()
            chunk_processor.reset_streaming_state()

            chunk_start = 0.0
            while chunk_start < duration:
                chunk_end = min(duration, chunk_start + chunk_size_sec)
                chunk_audio = chunk_processor.process_chunk(
                    clip_scheduler=scheduler,
                    chunk_start=chunk_start,
                    chunk_end=chunk_end,
                    role_ranges=role_ranges,
                    default_ducking=default_ducking,
                    default_compression=default_compression,
                )

                if config.master_gain != 0:
                    chunk_audio = chunk_audio.apply_gain(config.master_gain)

                if estimator is not None:
                    from audio_engine.dsp.loudness import audiosegment_to_float
                    rolling_gain = estimator.get_estimated_gain_db()
                    if rolling_gain != 0:
                        chunk_audio = chunk_audio.apply_gain(rolling_gain)
                    estimator.process_chunk(audiosegment_to_float(chunk_audio))
                elif gain_db != 0:
                    chunk_audio = chunk_audio.apply_gain(gain_db)

                if scene_eq:
                    chunk_audio = apply_scene_tonal_shaping(chunk_audio, scene_eq)

                if peak_estimator is not None:
                    from audio_engine.dsp.loudness import audiosegment_to_float
                    peak_estimator.process_chunk(audiosegment_to_float(chunk_audio))

                if peak_gain_db != 0:
                    chunk_audio = chunk_audio.apply_gain(peak_gain_db)

                # Master fade-out for last segment
                if config.master_fade_out:
                    fade_duration_sec = config.master_fade_out.get("duration", 10.0)
                    fade_ms = int(fade_duration_sec * 1000)
                    fade_ms = min(fade_ms, int(duration * 1000))
                    curve_str = config.master_fade_out.get("curve", None)
                    curve = FadeCurve.from_string(curve_str)
                    chunk_audio = apply_fade_out(
                        canvas=chunk_audio,
                        clip_start_ms=int(chunk_start * 1000),
                        clip_len_ms=len(chunk_audio),
                        project_len_ms=int(duration * 1000),
                        fade_ms=fade_ms,
                        curve=curve,
                    )

                writer.write_segment(chunk_audio)
                chunk_start = chunk_end

            writer.close()

        if config.normalize_peak:
            temp_output = f"{output_path}.tmp.wav"
            peak_estimator = StreamingPeakEstimator()
            render_pass(temp_output, peak_estimator=peak_estimator)

            lufs_gain_db = 0.0
            if config.loudness:
                measured_lufs = measure_lufs_from_file(temp_output)
                lufs_gain_db = compute_lufs_gain_db(
                    current_lufs=measured_lufs,
                    target_lufs=config.target_lufs,
                )
                logger.info(
                    "Streaming LUFS pass complete: measured %.2f, gain %.2f dB",
                    measured_lufs,
                    lufs_gain_db,
                )

            peak_after_lufs = peak_estimator.max_abs * (10 ** (lufs_gain_db / 20.0))
            peak_gain_db = compute_peak_gain_db(peak_after_lufs, config.peak_target_dbfs)

            render_pass(output_path, gain_db=lufs_gain_db, peak_gain_db=peak_gain_db)
            try:
                os.remove(temp_output)
            except OSError:
                logger.warning(f"Failed to remove temp file: {temp_output}")
        elif config.loudness and two_pass_lufs:
            temp_output = f"{output_path}.tmp.wav"
            render_pass(temp_output)
            measured_lufs = measure_lufs_from_file(temp_output)
            gain_db = compute_lufs_gain_db(
                current_lufs=measured_lufs,
                target_lufs=config.target_lufs,
            )
            logger.info(f"Streaming LUFS pass complete: measured {measured_lufs:.2f}, gain {gain_db:.2f} dB")
            render_pass(output_path, gain_db=gain_db)
            try:
                os.remove(temp_output)
            except OSError:
                logger.warning(f"Failed to remove temp file: {temp_output}")
        elif config.loudness:
            from audio_engine.streaming.loudness import StreamingLoudnessEstimator
            estimator = StreamingLoudnessEstimator(sample_rate=sample_rate, target_lufs=config.target_lufs)
            render_pass(output_path, estimator=estimator)
        else:
            render_pass(output_path)


# Backward compatibility: maintain render_timeline function
def render_timeline(timeline_path: str, output_path: str) -> None:
    """
    Render timeline to output audio file (backward compatibility function).
    
    This function maintains compatibility with existing code while using
    the new TimelineRenderer class internally.
    
    Args:
        timeline_path: Path to timeline JSON file
        output_path: Path to output WAV file
    """
    renderer = TimelineRenderer()
    renderer.render(timeline_path, output_path)
