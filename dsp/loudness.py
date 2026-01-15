import numpy as np
import pyloudnorm as pyln

from pydub import AudioSegment



def audiosegment_to_float(audio: AudioSegment) -> np.ndarray:
    """
    Convert AudioSegment to float32 numpy array (-1.0 to 1.0)
    """

    samples = np.array(audio.get_array_of_samples())

    if audio.channels > 1:
        samples = samples.reshape((-1, audio.channels))

    return samples.astype(np.float32) / (2 ** (8 * audio.sample_width - 1))


def measure_integrated_lufs(audio: AudioSegment) -> float:
    """
    measure integrated LUFS of an AudioSegment
    """

    meter = pyln.Meter(audio.frame_rate)
    samples = audiosegment_to_float(audio)

    return meter.integrated_loudness(samples)



def apply_lufs_target(
    audio: AudioSegment,
    target_lufs: float,
    max_boost_db: float = 6.0,
    max_cut_db: float = 10.0
) -> AudioSegment:
    """
    Apply loudness correction toward a target LUFS value
    while clamping extreme gain changes.
    """
    current_lufs = measure_integrated_lufs(audio)
    gain_db = target_lufs - current_lufs

    # Clamp gain
    if gain_db > max_boost_db:
        gain_db = max_boost_db
    elif gain_db < -max_cut_db:
        gain_db = -max_cut_db

    return audio.apply_gain(gain_db)
