"""
MasterProcessor handles master-level effects and final processing.
"""
from typing import Optional, Dict, Any
from pydub import AudioSegment

from utils.logger import get_logger
from renderer.config import RenderConfig
from dsp.fade_curves import FadeCurve
from dsp.fades import apply_fade_out

logger = get_logger(__name__)


class MasterProcessor:
    """Applies master-level effects to the final mixed audio."""
    
    def __init__(self):
        """Initialize MasterProcessor."""
        pass
    
    def process(
        self,
        audio: AudioSegment,
        config: RenderConfig
    ) -> AudioSegment:
        """
        Apply all master-level effects to the audio.
        
        Args:
            audio: Mixed audio segment
            config: Render configuration
        
        Returns:
            Processed audio with master effects applied
        """
        # Validate audio is not None
        if audio is None:
            logger.error("Cannot process master effects: audio is None")
            raise ValueError("Cannot process master effects: audio is None")
        
        # Master Gain
        if config.master_gain != 0:
            audio = audio + config.master_gain
            # Validate gain operation returned valid audio
            if audio is None:
                logger.error("Master gain operation returned None")
                raise ValueError("Master gain operation returned None")
            logger.debug(f"Applied master gain: {config.master_gain}dB")
        
        # LUFS Correction
        if config.loudness:
            try:
                from dsp.loudness import apply_lufs_target
                audio = apply_lufs_target(audio=audio, target_lufs=config.target_lufs)
                # Validate LUFS operation returned valid audio
                if audio is None:
                    logger.warning("LUFS normalization returned None, skipping")
                else:
                    logger.debug(f"Applied LUFS normalization to {config.target_lufs} LUFS")
            except Exception as e:
                logger.warning(f"Failed to apply LUFS normalization: {e}")
                # Ensure audio remains valid after exception
                if audio is None:
                    raise ValueError("Audio became None after LUFS normalization failure")
        
        # Peak Normalization
        if config.normalize_peak:
            try:
                from dsp.normalization import normalize_peak
                audio = normalize_peak(audio, target_dbfs=config.peak_target_dbfs)
                # Validate normalization returned valid audio
                if audio is None:
                    logger.warning("Peak normalization returned None, skipping")
                else:
                    logger.debug("Applied peak normalization")
            except Exception as e:
                logger.warning(f"Failed to apply peak normalization: {e}")
                # Ensure audio remains valid after exception
                if audio is None:
                    raise ValueError("Audio became None after peak normalization failure")
        
        # Master Fade Out
        if config.master_fade_out:
            try:
                fade_duration_sec = config.master_fade_out.get("duration", 10.0)
                fade_ms = int(fade_duration_sec * 1000)
                fade_ms = min(fade_ms, len(audio))
                
                # Extract curve type (defaults to LINEAR for backward compatibility)
                curve_str = config.master_fade_out.get("curve", None)
                curve = FadeCurve.from_string(curve_str)
                
                # Apply fade-out with specified curve
                # Use apply_fade_out function which supports curves
                audio = apply_fade_out(
                    canvas=audio,
                    clip_start_ms=0,
                    clip_len_ms=len(audio),
                    project_len_ms=len(audio),
                    fade_ms=fade_ms,
                    curve=curve
                )
                # Validate fade-out returned valid audio
                if audio is None:
                    logger.warning("Master fade-out returned None, skipping")
                else:
                    logger.debug(f"Applied master fade-out: {fade_duration_sec}s with {curve.value} curve")
            except Exception as e:
                logger.warning(f"Failed to apply master fade-out: {e}")
                # Ensure audio remains valid after exception
                if audio is None:
                    raise ValueError("Audio became None after master fade-out failure")
        
        # Final validation before returning
        if audio is None:
            logger.error("Audio is None after master processing")
            raise ValueError("Audio is None after master processing")
        
        return audio
