def interpolate_gain(start_gain: float, end_gain: float, progress: float) -> float:
    """
    Linear interpolation between two gain values.
    progress: 0.0 → start_gain, 1.0 → end_gain
    """
    progress = max(0.0, min(1.0, progress))
    return start_gain + (end_gain - start_gain) * progress
