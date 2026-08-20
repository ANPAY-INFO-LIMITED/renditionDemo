"""Shared utilities for shot segmentation.

Lives in modules/ so both the upload page (auto-segment after analysis) and
the shot segmentation page can reuse the same logic.
"""

import uuid


def format_timestamp(seconds: float) -> str:
    """Format timestamp to mm:ss"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def _build_segment_prompt_text(prompts: list) -> str:
    """
    Merge ScenePrompt objects into a single combined prompt string.

    Time ranges are expressed relative to the first prompt (00:00), since each
    segment will be generated as an independent video.
    """
    if not prompts:
        return ""

    base_time = prompts[0].start_time
    lines = []
    for p in prompts:
        rel_start = max(0.0, p.start_time - base_time)
        rel_end = max(0.0, p.end_time - base_time)
        time_range = f"{format_timestamp(rel_start)}-{format_timestamp(rel_end)}"
        parts = [time_range]
        if p.camera:
            parts.append(f"镜头:{p.camera}")
        if p.space:
            parts.append(f"空间:{p.space}")
        if p.time_atmosphere:
            parts.append(f"氛围:{p.time_atmosphere}")
        if p.opening_frame:
            parts.append(f"开场:{p.opening_frame}")
        if p.continuous_action:
            parts.append(f"动作:{p.continuous_action}")
        if p.end_state:
            parts.append(f"结尾:{p.end_state}")
        lines.append(" ".join(parts))

    return "\n".join(lines)


def segment_shots_into_groups(scene_prompts: list, max_duration: float = 15.0) -> list:
    """Group scene prompts into segments where total duration <= max_duration."""
    if not scene_prompts:
        return []

    segments = []
    current_group = []
    current_duration = 0.0

    for prompt in scene_prompts:
        duration = prompt.end_time - prompt.start_time

        if duration > max_duration:
            if current_group:
                segments.append({
                    'id': str(uuid.uuid4()),
                    'index': len(segments),
                    'total_duration': current_duration,
                    'start_time': current_group[0].start_time,
                    'end_time': current_group[-1].end_time,
                    'prompt_count': len(current_group),
                    'combined_prompt': _build_segment_prompt_text(current_group)
                })
                current_group = []
                current_duration = 0.0

            segments.append({
                'id': str(uuid.uuid4()),
                'index': len(segments),
                'total_duration': duration,
                'start_time': prompt.start_time,
                'end_time': prompt.end_time,
                'prompt_count': 1,
                'combined_prompt': _build_segment_prompt_text([prompt])
            })
        elif current_duration + duration > max_duration:
            if current_group:
                segments.append({
                    'id': str(uuid.uuid4()),
                    'index': len(segments),
                    'total_duration': current_duration,
                    'start_time': current_group[0].start_time,
                    'end_time': current_group[-1].end_time,
                    'prompt_count': len(current_group),
                    'combined_prompt': _build_segment_prompt_text(current_group)
                })
            current_group = [prompt]
            current_duration = duration
        else:
            current_group.append(prompt)
            current_duration += duration

    if current_group:
        segments.append({
            'id': str(uuid.uuid4()),
            'index': len(segments),
            'total_duration': current_duration,
            'start_time': current_group[0].start_time,
            'end_time': current_group[-1].end_time,
            'prompt_count': len(current_group),
            'combined_prompt': _build_segment_prompt_text(current_group)
        })

    return segments


def auto_segment_task(task, max_duration: float = 15.0) -> int:
    """
    Build shot_segments for the given task and persist them.

    Returns the number of segments produced (0 if there are no scene prompts
    or segments already exist and are up to date).
    """
    if not task or not task.scene_prompts:
        return 0

    segments = segment_shots_into_groups(task.scene_prompts, max_duration=max_duration)

    char_names = [c.name for c in (task.character_keyframes or []) if c.name]
    character_context = ", ".join(char_names) if char_names else ""

    task.shot_segments = [
        {
            'id': seg['id'],
            'index': seg['index'],
            'total_duration': seg['total_duration'],
            'start_time': seg['start_time'],
            'end_time': seg['end_time'],
            'prompt_count': seg['prompt_count'],
            'character_context': character_context,
            'combined_prompt': seg['combined_prompt']
        }
        for seg in segments
    ]

    return len(segments)
