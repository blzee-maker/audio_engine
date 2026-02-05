# 🎧 Audio Timeline Engine — Status & Design Notes

**Project:** Aud-Stories Audio Engine  
**Phase:** Advanced Features In Progress  
**Last Updated:** February 2026

---

## 1. Purpose of This Document

This file documents:

- ✅ What has been implemented successfully
- 🧠 Key engineering decisions taken
- ⚠️ Known limitations (intentional)
- 🔮 Guidelines for future upgrades

This is a living document and should be updated whenever a core behavior changes.

---

## 2. Current Engine Capabilities

### 2.1 Timeline & Rendering Core ✅

- JSON-driven audio timeline
- Deterministic rendering (same input → same output)
- Multi-track audio composition
- Timeline-based placement using absolute time (seconds → ms)
- Refactored architecture with clear separation of concerns

### 2.2 Scene System ✅

- Scene blocks compile into track clips
- Scenes are not rendered directly
- Scene preprocessing converts scenes → clips
- Scene boundaries respected strictly
- Scene energy mapping (0.0–1.0) drives music gain

**Key insight:**
> Scenes are author intent, not runtime entities

### 2.3 Rule System (Global + Scene Overrides) ✅

- `settings` define global defaults
- `scene.rules` override global settings
- Rules are merged during preprocessing
- Final merged rules are attached as `_rules` on each clip

**Important convention:**
- `rules` → external (JSON, author-facing)
- `_rules` → internal (engine-only, compiled)

### 2.4 Role-Based Ducking ✅

- Tracks have semantic roles (`voice`, `duckable`, `background`)
- Ducking rules defined declaratively
- Ducking applies only during overlapping time ranges
- Fade-in/out smoothing applied to ducking envelopes
- Scene-specific ducking overrides supported
- **SFX semantic roles** can participate in ducking (`sfx:impact`, `sfx:ambience`)

**Ducking Configuration:**
```json
"ducking": {
  "enabled": true,
  "mode": "audacity",
  "duck_amount": -6,
  "fade_down_ms": 500,
  "fade_up_ms": 500,
  "min_pause_ms": 300,
  "onset_delay_ms": 120,
  "rules": [
    { "when": "voice", "duck": ["background", "sfx:ambience"] },
    { "when": "sfx:impact", "duck": ["music"] }
  ]
}
```

### 2.5 Dialogue Compression ✅

- Applied only to `role = voice`
- Configurable threshold, ratio, attack, release, makeup gain
- Scene-level overrides supported
- Compression runs before fades and ducking

### 2.6 Fade In / Fade Out (Timeline-Based) ✅

**Important achievement:**
> Fades are applied after placement, in timeline space — not clip space.

**Why:**
- `AudioSegment.overlay()` does not preserve perceptual fades reliably
- Applying fades after placement mirrors DAW behavior

**Advanced Fade Curves (NEW):**
- **Linear** — Constant rate fade (default)
- **Logarithmic** — Slower start, faster end (natural fade-in)
- **Exponential** — Faster start, slower end (sharp transitions)

### 2.7 Scene Crossfade ✅

Scene crossfade is implemented as:
- Fade-out on outgoing clip
- Fade-in on incoming clip
- Explicit time overlap between scenes

**Key rule learned:**
> Fade ≠ Crossfade  
> Crossfade = Fade + Overlap

### 2.8 Overlap Auto-Fix ✅

- Detects overlapping clips on same track
- Shifts later clips forward
- Preserves loop duration
- Prevents timeline corruption from AI-generated input

### 2.9 EQ System ✅ (NEW)

**Intent-First Design:**
- Authors use semantic presets (`dialogue_clean`, `music_bed`)
- Engine handles frequency details internally

**Available Presets:**
| Preset | Intent |
|--------|--------|
| `dialogue_clean` | Clear voice, no rumble |
| `dialogue_warm` | Rich voice, less bright |
| `dialogue_broadcast` | Broadcast-ready voice |
| `music_full` | Full spectrum music |
| `music_bed` | Music as background bed |
| `background_soft` | Non-invasive ambience |
| `background_distant` | Far-away feel |
| `sfx_punch` | Impactful SFX |
| `sfx_subtle` | Gentle SFX presence |

**Scene-Level Tonal Shaping:**
- `tilt`: "warm", "neutral", "bright"
- `high_shelf`: dB adjustment above ~4kHz
- `low_shelf`: dB adjustment below ~200Hz

### 2.10 SFX Semantic Roles ✅ (NEW)

**Valid Semantic Roles:**
| Role | LUFS Target | Fade In | Fade Out | Curve |
|------|-------------|---------|----------|-------|
| `impact` | -18.0 | 0ms | 75ms | Exponential |
| `movement` | -20.0 | 150ms | 150ms | Linear |
| `ambience` | -22.0 | 750ms | 750ms | Logarithmic |
| `interaction` | -20.0 | 250ms | 250ms | Linear |
| `texture` | -24.0 | 1500ms | 1500ms | Logarithmic |

### 2.11 LUFS Loudness ✅

- Target: -20 LUFS (cinematic)
- Role-based loudness targets
- Safety clamping (max boost/cut limits)

### 2.12 Logging System ✅ (NEW)

- Structured logging with Python's `logging` module
- Configurable log levels (DEBUG, INFO, WARNING, ERROR)
- Performance timing for rendering stages

### 2.13 Debug Timeline View ✅

Human-readable timeline dump showing:
- Track
- Clip start/end
- Loop ranges
- Fade info
- Ducking & compression values

---

## 3. Key Engineering Decisions

### 3.1 Timeline-Space Processing

All perceptual effects (fade, ducking, compression) are reasoned in timeline space, not clip space.

**Reason:**
- Prevents overlay-related artifacts
- Ensures predictable interaction between systems

### 3.2 Defensive Handling of Clips

Any function that:
- Sorts by time
- Detects overlaps
- Applies transitions

**Must ignore clips without `start`.**

This prevents crashes during intermediate compilation stages.

### 3.3 Fade Strategy

Current fade implementation uses:
- Multiple curve types (linear, logarithmic, exponential)
- Timeline-space application for perceptual accuracy

### 3.4 Intent-First EQ

EQ is exposed through semantic presets rather than raw Hz values.
- Authors describe what they want
- Engine handles frequency knowledge internally
- Versionable presets for safe evolution

### 3.5 SFX Semantic/Mix Role Separation

- `role` = **mix_role** (foreground/background/voice)
- `semantic_role` = **what the sound represents** (impact, movement, etc.)

These are orthogonal concepts that answer different questions.

---

## 4. Known Limitations (Accepted)

These are not bugs, they are planned constraints.

### 4.1 No Reverb
- No spatial effects
- **Planned:** Advanced phase

### 4.2 Performance
- Entire project loaded into memory
- No parallelization
- **Planned:** Streaming, parallel processing

### 4.3 No API
- Command-line only
- **Planned:** REST API with FastAPI

---

## 5. Testing Status

### Completed Tests ✅
- Basic feature tests
- Intermediate feature interaction tests
- Fade-in / fade-out isolated tests
- Scene crossfade tests
- Ducking + crossfade overlap tests
- EQ preset application tests
- SFX semantic role tests
- Advanced fade curve tests

### Philosophy
> If debug output matches what you hear, the system is trusted

---

## 6. Audio Pipeline Order (DO NOT CHANGE)

```
1. Load Audio
2. Apply Track/Clip Gain
3. Apply EQ (role preset)      ← NEW
4. Apply SFX Processing        ← NEW
5. Apply Energy Ramp
6. Apply Ducking
7. Apply Dialogue Compression
8. Overlay to Canvas
9. Apply Scene Tonal Shaping   ← NEW
10. Apply Fades
──────────────────────────────
11. Track Mix
12. LUFS Loudness Correction
13. Master Gain
14. Peak Normalization
15. Export
```

**Reason:**
- EQ shapes frequencies before ducking (for cleaner separation)
- LUFS must operate on perceptual loudness of the full mix
- Peak normalization is safety, not loudness control
- Reordering breaks cinematic dynamics

---

## 7. Loudness Standard (Cinematic)

| Parameter | Value |
|-----------|-------|
| Integrated LUFS target | −20.0 |
| Dialogue anchor | ~−18 LUFS |
| True peak ceiling | −1.0 dBFS |

**Why:** Preserves dynamic range while maintaining clarity for story-driven audio.

---

## 8. Guidelines for Future Upgrades

Before adding a new feature, ask:

1. Does this operate in clip space or timeline space?
2. Does it interact with fades, ducking, or compression?
3. Can it break determinism?
4. Can it be disabled cleanly?

**If unclear → document before coding.**

---

## 9. Final Engineering Principle

> **Correctness → Predictability → Perceptual Quality**

We do not skip stages.

---

*Document updated: February 2026*
