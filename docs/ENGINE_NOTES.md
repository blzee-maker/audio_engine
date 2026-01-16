## Intermediate Phase — Frozen

DSP architecture stabilized:
- Ducking (envelope-based)
- Dialogue compression
- Peak normalization
- Clip fades

Renderer responsibilities reduced to orchestration only.
All DSP units independently tested and verified.

Further changes belong to Advanced phase only.



Audio Pipeline Order (DO NOT CHANGE)
Clip DSP
→ Track Mix
→ LUFS Loudness Correction
→ Master Gain
→ Peak Normalization
→ Export


Reason

LUFS must operate on perceptual loudness of the full mix

Peak normalization is safety, not loudness control

Reordering breaks cinematic dynamics

Loudness Standard (Cinematic)

Integrated LUFS target: −20.0

Dialogue anchor: ~ −18 LUFS

True peak ceiling: −1.0 dBFS

Why
This preserves dynamic range while maintaining clarity for story-driven audio.

LUFS Design Rules

LUFS correction is optional and explicit

LUFS correction is clamped

Max boost: +6 dB

Max cut: −10 dB

LUFS is applied once per render

This prevents:

Noise floor amplification

Over-compression

Double loudness correction

DSP Responsibility Boundaries
Layer	Responsibility
dsp/*	Pure signal processing only
utils/*	Math, ranges, debug
renderer.py	Orchestration only
scene_preprocessor.py	Structural timeline expansion

DSP modules must not:

Know about scenes

Know about tracks

Know about timeline JSON

Ducking Philosophy

Default ducking is envelope-based

Ducking reacts to dialogue ranges

Fade-down and fade-up are asymmetric

Behavior matches DAW-style sidechain ducking

This ensures:

Smooth transitions

No abrupt volume drops

Dialogue intelligibility





- Ducking uses a short onset delay (~120ms) to avoid perceptual pre-duck dips before dialogue is heard.
