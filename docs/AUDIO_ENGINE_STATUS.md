🎧 Audio Timeline Engine — Status & Design Notes

Project: Aud-Stories Audio Engine
Phase: Basic + Intermediate Completed
Last Updated: (add date)

1. Purpose of This Document

This file documents:

✅ What has been implemented successfully

🧠 Key engineering decisions taken

⚠️ Known limitations (intentional)

🔮 Guidelines for future upgrades

This is a living document and should be updated whenever a core behavior changes.

2. Current Engine Capabilities (Achieved)
2.1 Timeline & Rendering Core

JSON-driven audio timeline

Deterministic rendering (same input → same output)

Multi-track audio composition

Timeline-based placement using absolute time (seconds → ms)

2.2 Scene System

Scene blocks compile into track clips

Scenes are not rendered directly

Scene preprocessing converts scenes → clips

Scene boundaries respected strictly

Key insight:

Scenes are author intent, not runtime entities

2.3 Rule System (Global + Scene Overrides)

settings define global defaults

scene.rules override global settings

Rules are merged during preprocessing

Final merged rules are attached as _rules on each clip

Important convention:

rules → external (JSON, author-facing)

_rules → internal (engine-only, compiled)

2.4 Role-Based Ducking

Tracks have semantic roles (voice, duckable, background)

Ducking rules defined declaratively

Ducking applies only during overlapping time ranges

Fade-in/out smoothing applied to ducking envelopes

Scene-specific ducking overrides supported

2.5 Dialogue Compression

Applied only to role = voice

Configurable threshold, ratio, attack, release, makeup gain

Scene-level overrides supported

Compression runs before fades and ducking

2.6 Fade In / Fade Out (Timeline-Based)

Important achievement:
Fades are applied after placement, in timeline space — not clip space.

Why:

AudioSegment.overlay() does not preserve perceptual fades reliably

Applying fades after placement mirrors DAW behavior

Current approach:

Place clip on canvas

Apply fade on the exact timeline slice

2.7 Scene Crossfade

Scene crossfade is implemented as:

Fade-out on outgoing clip

Fade-in on incoming clip

Explicit time overlap between scenes

Key rule learned:

Fade ≠ Crossfade
Crossfade = Fade + Overlap

2.8 Overlap Auto-Fix

Detects overlapping clips on same track

Shifts later clips forward

Preserves loop duration

Prevents timeline corruption from AI-generated input

2.9 Debug Timeline View

Human-readable timeline dump

Shows:

Track

Clip start/end

Loop ranges

Fade info

Ducking & compression values

Defensive: skips clips without start

3. Key Engineering Decisions (Important)
3.1 Timeline-Space Processing

All perceptual effects (fade, ducking, compression) are reasoned in timeline space, not clip space.

Reason:

Prevents overlay-related artifacts

Ensures predictable interaction between systems

3.2 Defensive Handling of Clips

Any function that:

Sorts by time

Detects overlaps

Applies transitions

Must ignore clips without start

This prevents crashes during intermediate compilation stages.

3.3 Fade Strategy (Current)

Current fade implementation uses:

Linear fade

Pre-attenuation (e.g. -18 dB) to improve perceptual smoothness

This is intentional and temporary.

4. Known Limitations (Accepted for Now)

These are not bugs, they are planned constraints.

4.1 Fade Curves

Fades are linear, not logarithmic/exponential

Psychoacoustic accuracy is acceptable but not perfect

Planned upgrade:

Curve-based fades in Advanced phase

4.2 Loudness Standard

No LUFS normalization

Only peak normalization supported

Planned upgrade:

LUFS-based mastering

Platform presets (Spotify / Podcast / Audiobook)

4.3 DSP Scope

No EQ

No reverb

No true sidechain compression

Planned upgrade:

Pedalboard / DSP chain integration

5. Testing Status
Completed

Basic feature tests

Intermediate feature interaction tests

Fade-in / fade-out isolated tests

Scene crossfade tests

Ducking + crossfade overlap tests

Philosophy

If debug output matches what you hear, the system is trusted

6. Guidelines for Future Upgrades

Before adding a new feature, ask:

Does this operate in clip space or timeline space?

Does it interact with fades, ducking, or compression?

Can it break determinism?

Can it be disabled cleanly?

If unclear → document before coding.

7. Next Planned Phase (Advanced)

Planned future work:

Logarithmic / exponential fade curves

LUFS loudness normalization

True sidechain compression

DSP effect chains

API-based rendering (FastAPI)

Batch rendering & caching

8. Final Engineering Principle (Lock This In)

Correctness → Predictability → Perceptual Quality

We do not skip stages.




Ducking System v2 — Audacity Style

Envelope-based ducking

Timeline-aware (not clip-based)

Phases:

Fade down (pre-dialogue)

Duck hold

Fade up (post-dialogue)

Small dialogue gaps ignored via min_pause_ms

Enabled via:

"ducking": { "mode": "audacity" }


Status: Stable and locked for Intermediate phase