from pydub import AudioSegment

def apply_fade_in(
    canvas: AudioSegment,
    start_ms: int,
    fade_ms: int
) -> AudioSegment:
    """
    Apply a fade-in on the canvas starting at start_ms.
    """
    if fade_ms <= 0:
        return canvas

    before = canvas[:start_ms]
    middle = canvas[start_ms:start_ms + fade_ms].fade_in(fade_ms)
    after = canvas[start_ms + fade_ms:]

    return before + middle + after


def apply_fade_out(
    canvas: AudioSegment,
    clip_start_ms: int,
    clip_len_ms: int,
    project_len_ms: int,
    fade_ms: int
) -> AudioSegment:
    """
    Apply a fade-out at the end of a clip on the canvas.
    """
    if fade_ms <= 0:
        return canvas

    clip_end_ms = min(
        clip_start_ms + clip_len_ms,
        project_len_ms
    )

    fade_ms = min(fade_ms, clip_end_ms - clip_start_ms)
    if fade_ms <= 0:
        return canvas

    before = canvas[:clip_end_ms - fade_ms]
    middle = canvas[clip_end_ms - fade_ms:clip_end_ms].fade_out(fade_ms)
    after = canvas[clip_end_ms:]

    return before + middle + after