"""
SFX Processing Module

Handles sound effects processing based on semantic roles.
Semantic roles define what the sound represents (impact, movement, etc.),
which is separate from mix_role (where it sits in the mix hierarchy).
"""
from typing import Optional, Dict, Tuple
from pydub import AudioSegment

from dsp.fade_curves import FadeCurve
from utils.logger import get_logger

logger = get_logger(__name__)

# Valid semantic roles
VALID_SEMANTIC_ROLES = {"impact", "movement", "ambience", "interaction", "texture"}

# LUFS targets for each semantic role
SEMANTIC_ROLE_LUFS_TARGETS = {
    "impact": -18.0,
    "movement": -20.0,
    "interaction": -20.0,
    "ambience": -22.0,
    "texture": -24.0
}

# Default fade durations (in milliseconds) for each semantic role
SEMANTIC_ROLE_FADE_DEFAULTS = {
    "impact": {
        "fade_in_ms": 0,
        "fade_out_ms": 75,  # Short fade-out for sharp attacks
        "fade_in_curve": FadeCurve.LINEAR,
        "fade_out_curve": FadeCurve.EXPONENTIAL
    },
    "movement": {
        "fade_in_ms": 150,
        "fade_out_ms": 150,
        "fade_in_curve": FadeCurve.LINEAR,
        "fade_out_curve": FadeCurve.LINEAR
    },
    "ambience": {
        "fade_in_ms": 750,
        "fade_out_ms": 750,
        "fade_in_curve": FadeCurve.LOGARITHMIC,
        "fade_out_curve": FadeCurve.LOGARITHMIC
    },
    "interaction": {
        "fade_in_ms": 250,
        "fade_out_ms": 250,
        "fade_in_curve": FadeCurve.LINEAR,
        "fade_out_curve": FadeCurve.LINEAR
    },
    "texture": {
        "fade_in_ms": 1500,
        "fade_out_ms": 1500,
        "fade_in_curve": FadeCurve.LOGARITHMIC,
        "fade_out_curve": FadeCurve.LOGARITHMIC
    }
}


def get_sfx_loudness_target(semantic_role: Optional[str]) -> Optional[float]:
    """
    Get LUFS target for a semantic role.
    
    Args:
        semantic_role: Semantic role string (impact, movement, etc.)
        
    Returns:
        LUFS target value, or None if role is invalid/not specified
    """
    if not semantic_role or semantic_role not in VALID_SEMANTIC_ROLES:
        return None
    
    return SEMANTIC_ROLE_LUFS_TARGETS.get(semantic_role)


def get_sfx_fade_behavior(semantic_role: Optional[str]) -> Optional[Dict]:
    """
    Get default fade behavior for a semantic role.
    
    Args:
        semantic_role: Semantic role string (impact, movement, etc.)
        
    Returns:
        Dictionary with fade_in_ms, fade_out_ms, fade_in_curve, fade_out_curve,
        or None if role is invalid/not specified
    """
    if not semantic_role or semantic_role not in VALID_SEMANTIC_ROLES:
        return None
    
    return SEMANTIC_ROLE_FADE_DEFAULTS.get(semantic_role)


def apply_sfx_timing(audio: AudioSegment, semantic_role: Optional[str]) -> AudioSegment:
    """
    Apply role-specific micro-timing adjustments (v1: minimal only).
    
    This function only performs micro-timing adjustments:
    - Attack shaping (trimming silence at start)
    - Silence trimming at end
    
    It does NOT:
    - Shift audio across timeline
    - Add auto delays
    - Change timeline positions
    
    Args:
        audio: Audio segment to process
        semantic_role: Semantic role string
        
    Returns:
        Processed audio segment
    """
    if not semantic_role or semantic_role not in VALID_SEMANTIC_ROLES:
        return audio
    
    # v1: Only minimal micro-timing
    # For impacts, trim very short silence at start/end for sharp attacks
    if semantic_role == "impact":
        # Trim up to 10ms of silence at start and end
        silence_threshold_ms = 10
        # This is a placeholder - actual implementation would analyze audio
        # For now, return audio unchanged (minimal timing in v1)
        pass
    
    # For other roles, no timing adjustments in v1
    return audio


def apply_sfx_processing(
    audio: AudioSegment,
    semantic_role: Optional[str],
    scene_energy: float = 0.5,
    clip_rules: Optional[Dict] = None
) -> AudioSegment:
    """
    Main SFX processing function.
    
    Applies semantic role-based processing including:
    - Loudness targets (via balance module, not here)
    - Micro-timing adjustments
    
    Note: Loudness is applied separately via balance module.
    This function focuses on timing and other SFX-specific processing.
    
    Args:
        audio: Audio segment to process
        semantic_role: Semantic role string (impact, movement, etc.)
        scene_energy: Scene energy value (0.0-1.0)
        clip_rules: Optional clip rules dictionary
        
    Returns:
        Processed audio segment
    """
    if audio is None:
        raise ValueError("Cannot apply SFX processing: audio is None")
    
    if not semantic_role or semantic_role not in VALID_SEMANTIC_ROLES:
        # No SFX-specific processing if role is invalid/not specified
        return audio
    
    # Apply micro-timing adjustments
    audio = apply_sfx_timing(audio, semantic_role)
    
    # Future: Could add scene energy-based adjustments here
    # For v1, keep it minimal
    
    return audio
