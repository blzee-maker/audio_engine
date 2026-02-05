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
    streaming_enabled: bool = False
    chunk_size_sec: float = 1.0
    streaming_max_workers: int = 4
    streaming_two_pass_lufs: bool = True
    streaming_sample_rate: int = 44100
    streaming_channels: int = 2
    streaming_sample_width: int = 2
    
    @classmethod
    def from_timeline_settings(cls, settings: Dict[str, Any]) -> 'RenderConfig':
        """Create RenderConfig from timeline settings dictionary."""
        loudness_cfg = settings.get("loudness", {})
        fade_cfg = settings.get("master_fade_out", {})
        streaming_cfg = settings.get("streaming", {})
        
        return cls(
            target_lufs=loudness_cfg.get("target_lufs", -20.0) if loudness_cfg.get("enabled") else -20.0,
            normalize_peak=settings.get("normalize", False),
            peak_target_dbfs=-1.0,
            master_gain=settings.get("master_gain", 0.0),
            master_fade_out=fade_cfg if fade_cfg.get("enabled") else None,
            loudness=loudness_cfg if loudness_cfg.get("enabled") else None,
            default_silence=settings.get("default_silence", 0.0),
            streaming_enabled=bool(streaming_cfg.get("enabled", False)),
            chunk_size_sec=float(streaming_cfg.get("chunk_size_sec", 1.0)),
            streaming_max_workers=int(streaming_cfg.get("max_workers", 4)),
            streaming_two_pass_lufs=bool(streaming_cfg.get("two_pass_lufs", True)),
            streaming_sample_rate=int(streaming_cfg.get("sample_rate", 44100)),
            streaming_channels=int(streaming_cfg.get("channels", 2)),
            streaming_sample_width=int(streaming_cfg.get("sample_width", 2)),
        )
