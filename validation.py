import os
import json
from pydub import AudioSegment


class ValidationError(Exception):
    pass

def validate_timeline(timeline:dict):
    errors=[]
    warnings=[]

    # Project

    project =timeline.get("project")
    if not project:
        errors.append("Missing 'Project' Section")

    duration = project.get("duration") if project else None
    if not isinstance(duration,(int,float)) or duration <=0:
        errors.append("project duration must be a positive number")

    
    # Tracks

    tracks = timeline.get("tracks")
    if not isinstance(tracks, list):
        errors.append("'tracks' must be a list")
    
    # Tracks & Clip Checks

    for track in tracks or []:
        track_id = track.get("id","UNKNOWN_TRACK")

        clips = track.get("clips")

        if not isinstance(clips, list):
            errors.append(f"Track '{track_id}' clips must be a list")
            continue

        last_end = 0.0

        for clip in clips:
            file_path = clip.get("file")
            if not file_path:
                errors.append(f"Track '{track_id}': clip missing file path")
                continue

            if not os.path.exists(file_path):
                errors.append(f"Missing audio file:{file_path}")
                continue

            try:
                audio = AudioSegment.from_file(file_path)
                clip_duration = len(audio)/1000

            except Exception:
                errors.append(f"Unreadable audio file: {file_path}")
                continue

            start = clip.get("start", last_end)
            if start < 0:
                errors.append(f"Negative start time in '{file_path}'")

            if start > duration:
                warnings.append(
                    f"Clip '{file_path}' start after project end"
                )

            
            end = start + clip_duration

            if end > duration:
                warnings.append(
                    f"Clip '{file_path}' exceeds project duration"
                )

            
            # Overlap warning (Same Track)
            if start < last_end:
                warnings.append(
                    f"Overlap detected in track '{track_id}' at '{file_path}'"
                )

            # loop Logic 
            if clip.get("loop"):
                loop_until = clip.get("loop_until", duration)
                if loop_until <= start:
                    errors.append(
                        f"Invalid loop_until for '{file_path}'"
                    )

            last_end = max(last_end, end)


        if errors:
            raise ValidationError(
                "Validation Faild : \n" + "\n".join(errors)
            )

        
        return warnings