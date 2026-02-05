"""
TimelineRenderer orchestrates the entire rendering pipeline.
"""
import os
from typing import Dict, List, Tuple, Optional
from pydub import AudioSegment

from utils.logger import get_logger, log_performance
from validation import validate_timeline
from scene_preprocessor import preprocess_scenes
from autofix import auto_fix_overlaps
from exceptions import FileError, TimelineError
from renderer.config import RenderConfig
from renderer.clip_processor import ClipProcessor
from renderer.track_mixer import TrackMixer
from renderer.master_processor import MasterProcessor
from dsp.eq import apply_scene_tonal_shaping

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
        from utils.debug import debug_print_timeline
        debug_print_timeline(timeline)
        
        # Extract settings
        duration = timeline["project"]["duration"]
        default_ducking = settings.get("ducking")
        default_compression = settings.get("dialogue_compression")
        
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
