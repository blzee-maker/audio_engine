# Audio Engine Feature Audit

**Audit Date:** February 5, 2026  
**Auditor:** Om Jha  
**Scope:** Full repository scan — feature-completion verification  

---

## Fully Implemented & Verified

The following features are **defined**, **passed through the pipeline**, and **clearly applied to audio output**:

### Timeline & Scene Preprocessing
| Feature | Calculated In | Applied In | Verified |
|---------|--------------|------------|----------|
| Scene-to-clip expansion | `scene_preprocessor.py:preprocess_scenes()` | Timeline tracks | ✅ |
| Rule merging (Global → Scene → Clip) | `scene_preprocessor.py:merge_rules()` | `_rules` dict on each clip | ✅ |
| Scene crossfade injection | `scene_preprocessor.py:apply_scene_crossfades()` | Fade in/out values on clips | ✅ |
| Auto-fix overlaps | `autofix.py:auto_fix_overlaps()` | Clip start times adjusted | ✅ |
| Timeline validation | `validation.py:validate_timeline()` | Errors/warnings emitted | ✅ |

### Clip-Level DSP (Standard & Streaming)
| Feature | DSP Module | Applied In | Verified |
|---------|-----------|------------|----------|
| Track/clip gain | N/A (pydub) | `clip_processor.py:139-141` | ✅ |
| EQ presets (role-based & explicit) | `dsp/eq.py:apply_eq_preset()` | `clip_processor.py:146-157` | ✅ |
| SFX semantic role loudness | `dsp/balance.py:apply_role_loudness()` | `clip_processor.py:177-184` | ✅ |
| Energy ramp (background/music) | `utils/energy_ramp.py:apply_energy_ramp()` | `clip_processor.py:187-202` | ✅ |
| Dialogue density adjustment | N/A (direct gain) | `clip_processor.py:205-211` | ✅ |
| Looping | N/A (pydub) | `clip_processor.py:220-226` | ✅ |
| Ducking (Audacity mode) | `dsp/ducking.py:apply_envelope_ducking()` | `clip_processor.py:231-284` | ✅ |
| Dialogue compression | `dsp/compression.py:apply_dialogue_compression()` | `clip_processor.py:287-292` | ✅ |
| Fade in/out with curves | `dsp/fades.py`, `dsp/fade_curves.py` | `clip_processor.py:317-383` | ✅ |
| SFX fade defaults by semantic role | `dsp/sfx_processor.py:get_sfx_fade_behavior()` | `clip_processor.py:313-315, 333-347, 367-383` | ✅ |

### Track-Level Processing
| Feature | DSP Module | Applied In | Verified |
|---------|-----------|------------|----------|
| Role-based loudness (voice, music, background) | `dsp/balance.py:apply_role_loudness()` | `track_mixer.py:101-116` | ✅ |
| Track-level EQ preset override | `dsp/eq.py` | Passed to `clip_processor.py:146` | ✅ |

### Master Processing (Standard Render)
| Feature | DSP Module | Applied In | Verified |
|---------|-----------|------------|----------|
| Scene tonal shaping (tilt, shelves) | `dsp/eq.py:apply_scene_tonal_shaping()` | `timeline_renderer.py:227-239` | ✅ |
| Master gain | N/A (pydub) | `master_processor.py:43-49` | ✅ |
| LUFS normalization | `dsp/loudness.py:apply_lufs_target()` | `master_processor.py:52-65` | ✅ |
| Peak normalization | `dsp/normalization.py:normalize_peak()` | `master_processor.py:68-81` | ✅ |
| Master fade out with curves | `dsp/fades.py:apply_fade_out()` | `master_processor.py:84-113` | ✅ |

### Streaming Render
| Feature | Applied In | Verified |
|---------|------------|----------|
| Chunked processing | `streaming/chunk_processor.py` | ✅ |
| Clip scheduling (incl. loops) | `streaming/clip_scheduler.py` | ✅ |
| Per-chunk scene tonal EQ | `timeline_renderer.py:353-354` | ✅ |
| Two-pass LUFS normalization | `timeline_renderer.py:377-390` | ✅ |
| Single-pass LUFS estimation | `streaming/loudness.py:StreamingLoudnessEstimator` | ✅ |
| Master gain per chunk | `timeline_renderer.py:341-342` | ✅ |
| Master fade out per chunk | `timeline_renderer.py:356-370` | ✅ |

---

## Partially Implemented (Needs Completion)

### 1. SFX Micro-Timing Adjustments

**Status:** Placeholder only

| Aspect | Location |
|--------|----------|
| Calculated | `dsp/sfx_processor.py:apply_sfx_timing()` (line 96) |
| Where it stops | Function body is effectively `pass` for impact role (line 126) |
| Missing | Actual silence-trimming implementation |

**Evidence:**
```python
# dsp/sfx_processor.py lines 121-126
if semantic_role == "impact":
    # Trim up to 10ms of silence at start and end
    silence_threshold_ms = 10
    # This is a placeholder - actual implementation would analyze audio
    # For now, return audio unchanged (minimal timing in v1)
    pass
```

The function `apply_sfx_timing()` is called in `apply_sfx_processing()` (line 165), but performs no actual audio modification.

---

### 2. Scene Energy for SFX

**Status:** Passed but never used

| Aspect | Location |
|--------|----------|
| Calculated | `scene_preprocessor.py:164` — attached to `_rules` |
| Passed to | `dsp/sfx_processor.py:apply_sfx_processing()` via `clip_processor.py:166` |
| Where it stops | Comment on line 167 of `sfx_processor.py`: "Future: Could add scene energy-based adjustments here" |
| Missing | Any actual audio modification based on scene energy for SFX tracks |

**Evidence:**
```python
# dsp/sfx_processor.py lines 166-170
# Apply micro-timing adjustments
audio = apply_sfx_timing(audio, semantic_role)

# Future: Could add scene energy-based adjustments here
# For v1, keep it minimal
```

---

## Defined but Not Applied

### 1. `interpolate_gain()` Function

| Aspect | Details |
|--------|---------|
| File | `audio_engine/utils/energy_ramp.py` |
| Line | 6 |
| Definition | `def interpolate_gain(start_gain: float, end_gain: float, progress: float) -> float` |
| Import | Imported in `legacy_renderer.py:30` |
| Usage | **Never called anywhere** |

The `apply_energy_ramp()` function uses pydub's `fade_in()` / `fade_out()` as an approximation instead of sample-level interpolation using `interpolate_gain()`.

---

### 2. `StreamingCompressor` Class

| Aspect | Details |
|--------|---------|
| File | `audio_engine/dsp/streaming_compressor.py` |
| Line | 10 |
| Definition | Full stateful compressor with attack/release envelope |
| Usage | **Never imported or instantiated** |

This class was designed for chunk-by-chunk compression in streaming mode but is not used. The streaming pipeline does not apply dialogue compression statelessly across chunks.

---

### 3. Stateful Streaming EQ Filters

| Class | File | Line | Usage |
|-------|------|------|-------|
| `StreamingHighPass` | `dsp/streaming_eq.py` | 52 | **Never used** |
| `StreamingLowPass` | `dsp/streaming_eq.py` | 60 | **Never used** |
| `StreamingPeakEQ` | `dsp/streaming_eq.py` | 68 | **Never used** |

These classes provide stateful IIR filtering for proper DSP continuity across chunk boundaries. However, the streaming pipeline uses the same stateless `clip_processor.py` path, which applies `apply_eq_preset()` per-clip rather than maintaining filter state across chunks.

**Implication:** EQ filtering in streaming mode may have discontinuities at chunk boundaries for clips that span multiple chunks.

---

### 4. `ChunkLoader` Class

| Aspect | Details |
|--------|---------|
| File | `audio_engine/streaming/chunk_loader.py` |
| Line | 25 |
| Exported | `streaming/__init__.py:5` |
| Usage | **Never instantiated** |

The streaming pipeline uses `AudioSegment.from_file()` with `start_second` and `duration` parameters directly in `chunk_processor.py:70-74` instead of the `ChunkLoader` abstraction.

---

## Inconsistencies Between Standard vs Streaming

### 1. Peak Normalization

| Mode | Behavior | Location |
|------|----------|----------|
| Standard | Applied via `normalize_peak()` | `master_processor.py:68-81` |
| Streaming | **Explicitly skipped** | `timeline_renderer.py:314-315` |

**Evidence:**
```python
# timeline_renderer.py lines 314-315
if config.normalize_peak:
    logger.warning("Peak normalization not supported in streaming mode; skipping.")
```

---

### 2. EQ Presets in Legacy Renderer

| Renderer | EQ Applied |
|----------|------------|
| Modular (`TimelineRenderer`) | ✅ Yes — `clip_processor.py:146-157` |
| Legacy (`legacy_renderer.py`) | ❌ No — EQ presets are not applied |

The `legacy_renderer.py` does not import or call `apply_eq_preset()`. It processes clips via `apply_clip()` which lacks the EQ step present in the modular `ClipProcessor`.

---

### 3. Stateful DSP Across Chunks

| DSP Stage | Standard | Streaming | Continuity Issue |
|-----------|----------|-----------|------------------|
| EQ filters | Per-clip (stateless) | Per-clip (stateless) | Potential artifacts at chunk boundaries |
| Compression | Per-clip | Not applied | Dialogue compression skipped in streaming |
| Ducking | Per-clip with timeline ranges | Per-clip with timeline ranges | OK — ranges are absolute |

**Note:** Stateful streaming DSP classes exist (`StreamingCompressor`, `StreamingHighPass`, etc.) but are not integrated.

---

### 4. SFX Processing

| Mode | SFX Semantic Processing |
|------|------------------------|
| Standard | ✅ Applied via `apply_sfx_processing()` |
| Streaming | ✅ Applied via same `clip_processor.py` |

No inconsistency — both modes use the same `ClipProcessor`.

---

## Open Questions / Ambiguities

### 1. Dialogue Density: Ratio vs Label

**Observation:** Both `dialogue_density` (ratio, 0.0-1.0) and `dialogue_density_label` ("low"/"medium"/"high") are calculated and stored in `_rules`.

| Variable | Calculated In | Used In |
|----------|--------------|---------|
| `dialogue_density` (ratio) | `scene_preprocessor.py:160` | **Nowhere** |
| `dialogue_density_label` | `scene_preprocessor.py:161` | `clip_processor.py:205` |

**Ambiguity:** The continuous ratio is never used. Only the categorical label is applied. The ratio could enable more granular adjustment, but this is unclear if intentional.

---

### 2. Energy Ramp Approximation

**Observation:** The `apply_energy_ramp()` function does not perform true sample-level gain interpolation. Instead, it:

1. Applies `start_gain` to the ramp portion
2. Uses pydub's `fade_in()` or `fade_out()` based on gain direction
3. Applies `target_gain` to the rest

**Evidence:**
```python
# utils/energy_ramp.py lines 60-75
# Apply starting gain to ramp portion
ramp_part = ramp_part + start_gain

# Apply fade based on gain direction
gain_delta = target_gain - start_gain
if gain_delta < 0:
    ramp_part = ramp_part.fade_out(ramp_duration_ms)
else:
    ramp_part = ramp_part.fade_in(ramp_duration_ms)
```

**Ambiguity:** The `interpolate_gain()` function exists but is unused. It's unclear if the fade approximation is intentional or a simplification that should be replaced with proper interpolation.

---

### 3. Scene Crossfade Overlap Behavior

**Observation:** `apply_scene_crossfades()` adjusts clip timing:

```python
# scene_preprocessor.py lines 63-69
a["fade_out"] = max(a.get("fade_out",0), duration)
b["fade_in"] = max(b.get("fade_in",0), duration)
b["start"] -= duration  # This creates the overlap
```

**Ambiguity:** The documentation states "Overlaps scenes slightly" but the implementation literally moves the next clip's start time backward. This may cause unexpected behavior if clips are close but not exactly touching, due to the `abs(end_a - start_b) < 0.05` tolerance check.

---

### 4. Ducking "Scene" Mode

**Observation:** Two ducking modes exist:

| Mode | Implementation |
|------|----------------|
| `"audacity"` | Envelope-based ducking with fades |
| `"scene"` | Simple gain adjustment: `audio + duck_amount` |

**Evidence:**
```python
# clip_processor.py lines 273-282
if ducking_cfg.get("mode") == "audacity":
    audio = self.ducking_func(...)

if ducking_cfg.get("mode") == "scene":
    audio = audio + ducking_cfg["duck_amount"]
```

**Ambiguity:** The "scene" mode applies constant gain regardless of dialogue timing. This doesn't match typical ducking semantics and may be a legacy fallback or placeholder.

---

## Summary Table

| Category | Count |
|----------|-------|
| Fully Implemented | 25+ features |
| Partially Implemented | 2 features |
| Defined but Not Applied | 4 components |
| Standard/Streaming Inconsistencies | 4 items |
| Open Questions | 4 ambiguities |

---

## Critical Gaps Requiring Attention

1. **`StreamingCompressor`** — Dialogue compression is unavailable in streaming mode
2. **Stateful streaming EQ** — Potential audio artifacts at chunk boundaries
3. **Peak normalization** — Not available in streaming mode
4. **SFX micro-timing** — Placeholder code only
5. **Scene energy for SFX** — Passed but unused

---

*This audit is read-only. No code changes have been made.*
