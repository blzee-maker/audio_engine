import json
import os
import time

from pydub.effects import compress_dynamic_range
from pydub import AudioSegment

from validation import validate_timeline
from scene_preprocessor import preprocess_scenes
from autofix import auto_fix_overlaps

# DSP features
from dsp.ducking import apply_envelope_ducking
from dsp.compression import apply_dialogue_compression
from dsp.normalization import normalize_peak
from dsp.fades import apply_fade_in, apply_fade_out
from dsp.loudness import apply_lufs_target
from dsp.balance import apply_role_loudness


from utils.debug import debug_print_timeline

def load_timeline(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)

def create_canvas(duration_seconds: float)-> AudioSegment:
    return AudioSegment.silent(duration = int(duration_seconds * 1000))


def get_role_ranges(tracks):
    """
    Returns:
    {
        role_name:[(start,end),...]
    }
    """

    role_ranges ={}

    for track in tracks:
        role = track.get("role")
        if not role:
            continue

        for clip in track.get("clips",[]):
            start = clip.get("start",0)
            audio = AudioSegment.from_file(clip["file"])
            duration = len(audio)/1000.0
            end = start + duration

            role_ranges.setdefault(role,[]).append((start,end))

    return role_ranges


def apply_clip(canvas: AudioSegment, clip: dict, track_gain: float, project_duration: float, role_ranges=None,track_role = None, default_ducking=None, default_compression=None)-> AudioSegment:
    audio = AudioSegment.from_file(clip["file"])

    clip_rules = clip.get("_rules",{})

    ducking_cfg = clip_rules.get("ducking", default_ducking)
    compression_cfg = clip_rules.get(
        "dialogue_compression", default_compression
    )

    # Gain Handling
    audio = audio + track_gain
    if "gain" in clip:
        audio = audio + clip["gain"]

    # 🎤 Dialogue Compression
    if track_role == "voice" and compression_cfg and compression_cfg.get("enabled"):
        audio = apply_dialogue_compression(audio, compression_cfg)

    start_sec = clip["start"]
    start_ms = int(start_sec * 1000)

    # Looping Logic
    if clip.get("loop", False):
        loop_until = clip.get("loop_until", project_duration)
        loop_duration_ms = int((loop_until - start_sec)*1000)

        if loop_duration_ms > 0:
            loops = audio * ((loop_duration_ms // len(audio))+1)
            audio = loops[:loop_duration_ms]

        # Ducking (Audacity-style or fallback)
    if ducking_cfg and role_ranges:
        for rule in ducking_cfg.get("rules", []):
            when_role = rule["when"]

            if when_role in role_ranges and track_role in rule["duck"]:
                if ducking_cfg.get("mode") == "audacity":
                    audio = apply_envelope_ducking(
                        audio=audio,
                        clip_start_sec=start_sec,
                        dialogue_ranges=role_ranges[when_role],
                        cfg=ducking_cfg
                    )

    canvas = canvas.overlay(audio, position=start_ms)

    # Fade In
    if "fade_in" in clip:
        canvas = apply_fade_in(
            canvas=canvas,
            start_ms=start_ms,
            fade_ms=int(clip["fade_in"] * 1000)
        )

    # Fade Out
    if "fade_out" in clip:
        canvas = apply_fade_out(
            canvas=canvas,
            clip_start_ms=start_ms,
            clip_len_ms=len(audio),
            project_len_ms=int(project_duration * 1000),
            fade_ms=int(clip["fade_out"] * 1000)
        )

    
    return canvas
    

# Currently not in use - because of scenes but use full for timelines without scenes
# def process_clips(track, default_silence):
#     processed=[]
#     current_time = 0.0

#     for clip in track["clips"]:
#         clip = clip.copy()

#         if "start" not in clip:
#             clip["start"]= current_time
    
#         processed.append(clip)

#         if "start" not in clip:

#             audio = AudioSegment.from_file(clip["file"])
#             duration = len(audio)/1000.0

#             current_time = clip["start"] + duration + default_silence

#     # sort by start time

#     processed.sort(key=lambda c:c["start"])
#     return processed


def render_timeline(timeline_path:str, output_path:str):
    timeline = load_timeline(timeline_path)

    # Scene Preprocessing
    timeline = preprocess_scenes(timeline)

    # Auto-fix overlaps (per track)
    settings = timeline.get("settings",{})
    min_gap = settings.get("default_silence",0.0)

    for track in timeline.get("tracks",[]):
        auto_fix_overlaps(track, min_gap=min_gap)

    # validate
    warnings = validate_timeline(timeline)
    for w in warnings:
        print(f"⚠ WARNING: {w}")

    
    # Debug timeline print
    debug_print_timeline(timeline)

    duration = timeline["project"]["duration"]
    settings = timeline.get("settings",{})
    
    role_ranges = None

    default_ducking = settings.get("ducking")
    default_silence = settings.get("default_silence",0)
    default_compression = settings.get("dialogue_compression")

    
    if default_ducking and default_ducking.get("enabled"):
        role_ranges = get_role_ranges(timeline["tracks"])

    canvas = create_canvas(duration)

    for track in timeline["tracks"]:
        track_gain = track.get("gain",0)
        track_role = track.get("role")
        clips = track["clips"]

        track_buffer = create_canvas(duration)

        for clip in clips:
            track_buffer = apply_clip(
                track_buffer, 
                clip, 
                track_gain,
                duration,
                role_ranges=role_ranges,
                track_role=track_role,
                default_ducking=default_ducking,
                default_compression=default_compression
            )

        track_buffer = apply_role_loudness(track_buffer, track_role)

        canvas = canvas.overlay(track_buffer)

    # Master Gain

    master_gain = settings.get("master_gain",0)
    canvas = canvas + master_gain

    # LUFS Correction

    loudness_cfg = settings.get("loudness")

    if loudness_cfg and loudness_cfg.get("enabled"):
        canvas = apply_lufs_target(
            audio = canvas,
            target_lufs = loudness_cfg.get("target_lufs",-20.0)
        )

    # Normalization

    if settings.get("normalize", False):
        canvas = normalize_peak(canvas, target_dbfs=-1.0)

    os.makedirs(os.path.dirname(output_path),exist_ok=True)
    canvas.export(output_path, format="wav")

