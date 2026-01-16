from copy import deepcopy

def merge_rules(global_rules:dict,scene_rules:dict)->dict:
    """
    Scene rules override global rules(shallow merge).
    """

    merged={}

    for key, value in global_rules.items():
        merged[key]=value.copy() if isinstance(value, dict) else value
    
    for key, value in scene_rules.items():
        if key in merged and isinstance(merged[key],dict):
            merged[key].update(value)
        else:
            merged[key]=value

    return merged


def apply_scene_crossfades(track_clips, default_duration):
    
    """
    Adds fade_out to clip[i] and fade_in to clip[i+1]
    when they touch (or nearly touch) in time.
    """

    # sort by start time
    track_clips = [c for c in track_clips if "start" in c]
    
    if len(track_clips) < 2:
        return

    track_clips.sort(key=lambda c: c["start"])

    for i in range(len(track_clips)-1):
        a = track_clips[i]
        b = track_clips[i+1]

        # only crossfade scene-generated clips
        if "_rules" not in a or "_rules" not in b:
            continue
        
        end_a = a.get("loop_until", a["start"])
        start_b =  b["start"]

        #if they touch(or are very close), crossfade

        if abs(end_a - start_b)< 0.05:
            # scene override > global default
            scene_rules = b.get("_rules", {})
            cf = scene_rules.get("scene_crossfade",{})
            duration = cf.get("duration", default_duration)

            # inject fades
            a["fade_out"] = max(a.get("fade_out",0),duration)
            b["fade_in"] = max(b.get("fade_in",0), duration)

            b["start"] -= duration

            if b["start"] < 0:
                b["start"] = 0

def preprocess_scenes(timeline:dict)->dict:
    """
    Convert scene blocks into normal track clips.
    Mutates and returns timeline.
    """

    scenes = timeline.get("scenes",[])
    if not scenes:
        return timeline 
    
    global_settings = timeline.get("settings",{})

    # building a map

    track_map = {}
    for track in timeline.get("tracks",[]):
        track.setdefault("clips",[])
        track_map[track["id"]] = track

    for scene in scenes:
        scene_start = scene["start"]
        scene_end = scene_start + scene["duration"]

        scene_tracks = scene.get("tracks",{})
        scene_rules =  scene.get("rules",{})

        # merge global + scene rules

        effective_rules = merge_rules(global_settings, scene_rules)

        for track_id, clips in scene_tracks.items():
            if track_id not in track_map:
                raise ValueError(
                    f"Scene references unknown track '{track_id}"
                )

            for clip in clips:
                new_clip = deepcopy(clip)

                new_clip["start"] = scene_start + clip.get("offset",0)

                #Auto-loop till scene end

                if new_clip.get("loop"):
                    new_clip["loop_until"] = scene_end

                # attach scene rules to clip
                new_clip["_rules"] = effective_rules.copy()
                
                #attatch scene energy
                new_clip["_rules"]["scene_energy"]= scene.get("energy", 0.5)
                
                track_map[track_id]["clips"].append(new_clip)
                print(track_map["music"]["clips"])

    # Scene Crossfades (Per track)

    settings = timeline.get("settings",{})
    sc_cfg = settings.get("scene_crossfade",{})

    if sc_cfg.get("enabled", False):
        default_duration = sc_cfg.get("duration",1.5)

        for track in timeline.get("tracks",[]):
            clips = track.get("clips",[])
            apply_scene_crossfades(clips, default_duration)

    return timeline