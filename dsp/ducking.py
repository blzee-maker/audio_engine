from pydub import AudioSegment

from utils.ranges import merge_ranges



# this is static ducking -> updated version is apply_ducking()
def apply_simple_ducking(audio,clip_start,role_ranges,duck_roles,duck_db,fade_ms):
    output = audio

    for role in duck_roles:
        for r_start, r_end in role_ranges.get(role,[]):
            overlap_start=max(r_start - clip_start,0)
            overlap_end = min(r_end - clip_start, len(audio)/1000)

            if overlap_start < overlap_end:
                s_ms = int(overlap_start * 1000)
                e_ms = int(overlap_end * 1000)

                before = output[:s_ms]
                during = output[s_ms:e_ms].apply_gain(duck_db)
                after = output[e_ms:]

                during = during.fade_in(fade_ms).fade_out(fade_ms)
                output = before + during + after
            
    return output

def apply_envelope_ducking(audio: AudioSegment, clip_start_sec: float, dialogue_ranges, cfg: dict) -> AudioSegment:

    duck_db = cfg["duck_amount"]
    fade_down = cfg["fade_down_ms"]
    fade_up = cfg["fade_up_ms"]
    min_pause = cfg["min_pause_ms"]
    delay_ms = cfg.get("onset_delay_ms", 0) / 1000.0

    ranges = merge_ranges(dialogue_ranges, min_pause)
    output = audio

    for start, end in ranges:
        start += delay_ms
        rel_start = int((start - clip_start_sec) * 1000)
        rel_end = int((end - clip_start_sec) * 1000)

        rel_start = max(0, rel_start)
        rel_end = min(len(output), rel_end)

        if rel_start >= rel_end:
            continue

        # 🔽 Fade down BEFORE dialogue
        down_start = max(0, rel_start - fade_down)
        down_end = rel_start

        if down_end > down_start:
            output = (
                output[:down_start] +
                output[down_start:down_end].fade_out(fade_down) +
                output[down_end:]
            )

        # 🔇 Duck hold
        output = (
            output[:rel_start] +
            output[rel_start:rel_end].apply_gain(duck_db) +
            output[rel_end:]
        )

        # 🔼 Fade up AFTER dialogue
        up_start = rel_end
        up_end = min(len(output), rel_end + fade_up)

        if up_end > up_start:
            output = (
                output[:up_start] +
                output[up_start:up_end].fade_in(fade_up) +
                output[up_end:]
            )

    return output
