from pydub import AudioSegment
from dsp.loudness import apply_lufs_target


ROLE_LUFS_TARGETS = {
    "voice": -18.0,
    "music": -28.0,
    "background": -30.0,
    "sfx": -20.0
}


def apply_role_loudness(
    audio: AudioSegment,
    role: str
) -> AudioSegment:
    """
    Apply LUFS target based on track role.
    """
    if role not in ROLE_LUFS_TARGETS:
        return audio  # Unknown role → no change

    target_lufs = ROLE_LUFS_TARGETS[role]
    return apply_lufs_target(audio, target_lufs)
