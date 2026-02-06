# Audio Engine Feature Audit

**Audit Date:** February 5, 2026  
**Last Updated:** February 6, 2026  
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
| Calculated | `dsp/sfx_processor.py:apply_sfx_timing()` (line 157) |
| Where it stops | Function body is effectively `pass` for impact role (line 182-187) |
| Missing | Actual silence-trimming implementation |

**Evidence:**

```python
# dsp/sfx_processor.py lines 182-187
if semantic_role == "impact":
    # Trim up to 10ms of silence at start and end
    silence_threshold_ms = 10
    # This is a placeholder - actual implementation would analyze audio
    # For now, return audio unchanged (minimal timing in v1)
    pass
```

The function `apply_sfx_timing()` is called in `apply_sfx_processing()` (line 226), but performs no actual audio modification.

---

## Recently Implemented

### Scene Energy for SFX

**Status:** ✅ Implemented

| Aspect | Location |
|--------|----------|
| Calculated | `scene_preprocessor.py:164` — attached to `_rules` |
| Applied in | `dsp/sfx_processor.py:apply_sfx_processing()` (lines 228-232) |
| Behavior | Role-specific linear gain from normalized scene energy (-1.0 to +1.0) |
| Overrides | Optional per-clip `clip_rules.sfx_scene_energy_gain` |

---

## Defined but Unused

### 1. `interpolate_gain()` Function

| Aspect | Details |
|--------|---------|
| File | `audio_engine/utils/energy_ramp.py` |
| Line | 6 |
| Definition | `def interpolate_gain(start_gain: float, end_gain: float, progress: float) -> float` |
| Import | Imported in `legacy_renderer.py:30` |
| Usage | **Never called anywhere** |

The `apply_energy_ramp()` function uses pydub's `fade_in()` / `fade_out()` as an approximation instead of sample-level interpolation using `interpolate_gain()`.

Defined for future sample-accurate ramps; current implementation uses pydub fades as a perceptual approximation.

---

## Streaming Infrastructure (Implemented)

### 1. `StreamingCompressor` Class

| Aspect | Details |
|--------|---------|
| File | `audio_engine/dsp/streaming_compressor.py` |
| Line | 10 |
| Definition | Full stateful compressor with attack/release envelope |
| Usage | ✅ **Used in streaming chunk processing for voice compression** |

This class is instantiated in the streaming pipeline and applied per voice track buffer to preserve compression continuity across chunks (`chunk_processor.py:221-237`).

---

### 2. Stateful Streaming EQ Filters

| Class | File | Line | Usage |
|-------|------|------|-------|
| `StreamingHighPass` | `dsp/streaming_eq.py` | 52 | ✅ **Used in streaming chunk processing** |
| `StreamingLowPass` | `dsp/streaming_eq.py` | 60 | ✅ **Used in streaming chunk processing** |
| `StreamingPeakEQ` | `dsp/streaming_eq.py` | 68 | ✅ **Used in streaming chunk processing** |

These classes back streaming EQ in `chunk_processor.py:68-101, 170-187`, keeping filter state per clip across chunks while `clip_processor.py` skips re-applying EQ.

---

### 3. `ChunkLoader` Class

| Aspect | Details |
|--------|---------|
| File | `audio_engine/streaming/chunk_loader.py` |
| Line | 25 |
| Exported | `streaming/__init__.py:5` |
| Usage | ✅ **Used by `ChunkProcessor` for streaming slices** |

The streaming pipeline uses `ChunkLoader.get_chunk()` in `chunk_processor.py:149-156` to load slices and resample consistently.

---

## Standard vs Streaming Parity (Resolved)

### 1. Peak Normalization

| Mode | Behavior | Location |
|------|----------|----------|
| Standard | Applied via `normalize_peak()` | `master_processor.py:68-81` |
| Streaming | ✅ Applied via two-pass peak gain | `timeline_renderer.py:386-420` |

**Evidence:**
```python
# timeline_renderer.py
if config.normalize_peak:
    temp_output = f"{output_path}.tmp.wav"
    peak_estimator = StreamingPeakEstimator()
    render_pass(temp_output, peak_estimator=peak_estimator)
    # ...
    peak_gain_db = compute_peak_gain_db(peak_after_lufs, config.peak_target_dbfs)
    render_pass(output_path, gain_db=lufs_gain_db, peak_gain_db=peak_gain_db)
```

---

### 2. EQ Presets in Legacy Renderer

| Renderer | EQ Applied |
|----------|------------|
| Modular (`TimelineRenderer`) | ✅ Yes — `clip_processor.py:146-157` |
| Legacy (`legacy_renderer.py`) | ✅ Yes — `legacy_renderer.py:156-196` |

The `legacy_renderer.py` now applies EQ presets inside `apply_clip()` with the same priority as the modular renderer (clip > track > role default), using `apply_eq_preset()` and `get_preset_for_role()`.

True-peak limiting is not implemented (intentional).

---

### 3. Stateful DSP Across Chunks

| DSP Stage | Standard | Streaming | Continuity Issue |
|-----------|----------|-----------|------------------|
| EQ filters | Per-clip (stateless) | Per-clip (stateful across chunks) | Resolved for chunk boundaries |
| Compression | Per-clip | Track-level (stateful across chunks) | Resolved for voice tracks |
| Ducking | Per-clip with timeline ranges | Per-clip with timeline ranges | OK — ranges are absolute |

**Note:** Stateful streaming DSP classes are now integrated for compression and EQ. Ducking remains stateless by design.

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
| Partially Implemented | 1 feature (SFX micro-timing) |
| Defined but Unused | 1 component (`interpolate_gain()`) |
| Standard/Streaming Inconsistencies | 0 (all resolved) |
| Open Questions | 4 ambiguities |

---

## Critical Gaps Requiring Attention

1. **SFX micro-timing** — Placeholder code only (`sfx_processor.py:182-187`)

---

## Resolved Since Initial Audit

The following items were previously listed as gaps but have since been implemented:

| Item | Resolution |
|------|------------|
| `StreamingCompressor` | ✅ Now used in `chunk_processor.py:221-237` for voice tracks |
| Stateful streaming EQ | ✅ Implemented in `chunk_processor.py:68-101, 170-187` |
| Peak normalization (streaming) | ✅ Two-pass implementation in `timeline_renderer.py:393-418` |
| Scene energy for SFX | ✅ Applied in `sfx_processor.py:228-232` |
| `ChunkLoader` | ✅ Used in `chunk_processor.py:103-108, 149-156` |

---

*Last updated: February 6, 2026*
