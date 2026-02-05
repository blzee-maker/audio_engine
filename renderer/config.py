"""
Configuration dataclass for render settings.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class RenderConfig:
    """Configuration for rendering operations."""
    target_lufs: float = -20.0
    normalize_peak: bool = False
    peak_target_dbfs: float = -1.0
    master_gain: float = 0.0
    master_fade_out: Optional[Dict[str, Any]] = None
    loudness: Optional[Dict[str, Any]] = None
    default_silence: float = 0.0
    
    @classmethod
    def from_timeline_settings(cls, settings: Dict[str, Any]) -> 'RenderConfig':
        """Create RenderConfig from timeline settings dictionary."""
        loudness_cfg = settings.get("loudness", {})
        fade_cfg = settings.get("master_fade_out", {})
        
        return cls(
            target_lufs=loudness_cfg.get("target_lufs", -20.0) if loudness_cfg.get("enabled") else -20.0,
            normalize_peak=settings.get("normalize", False),
            peak_target_dbfs=-1.0,
            master_gain=settings.get("master_gain", 0.0),
            master_fade_out=fade_cfg if fade_cfg.get("enabled") else None,
            loudness=loudness_cfg if loudness_cfg.get("enabled") else None,
            default_silence=settings.get("default_silence", 0.0)
        )
