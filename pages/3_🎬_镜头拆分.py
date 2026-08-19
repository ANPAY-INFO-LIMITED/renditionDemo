"""Page 3: Shot Segmentation - Split shots into sub-video prompts"""

import streamlit as st
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules import Config, TaskManager, TaskStatus


def format_timestamp(seconds: float) -> str:
    """Format timestamp to mm:ss"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def get_duration_from_prompt(prompt: ScenePrompt) -> float:
    """Calculate duration from scene prompt"""
    return prompt.end_time - prompt.start_time


def segment_shots_into_groups(scene_prompts: list, max_duration: float = 15.0) -> list:
    """
    Group scene prompts into segments where total duration <= max_duration.
    Each segment represents a sub-video prompt.
    
    Args:
        scene_prompts: List of ScenePrompt objects
        max_duration: Maximum duration for each segment in seconds (default 15)
    
    Returns:
        List of dicts with segment info and contained prompts
    """
    if not scene_prompts:
        return []
    
    segments = []
    current_group = []
    current_duration = 0.0
    
    for prompt in scene_prompts:
        duration = get_duration_from_prompt(prompt)
        
        # If single prompt exceeds max_duration, it still goes in its own segment
        if duration > max_duration:
            # First, save current group if not empty
            if current_group:
                segments.append({
                    'id': str(uuid.uuid4()),
                    'index': len(segments),
                    'prompts': current_group,
                    'total_duration': current_duration,
                    'start_time': current_group[0].start_time,
                    'end_time': current_group[-1].end_time
                })
                current_group = []
                current_duration = 0.0
            
            # Add the oversized prompt as its own segment
            segments.append({
                'id': str(uuid.uuid4()),
                'index': len(segments),
                'prompts': [prompt],
                'total_duration': duration,
                'start_time': prompt.start_time,
                'end_time': prompt.end_time
            })
        elif current_duration + duration > max_duration:
            # Save current group
            if current_group:
                segments.append({
                    'id': str(uuid.uuid4()),
                    'index': len(segments),
                    'prompts': current_group,
                    'total_duration': current_duration,
                    'start_time': current_group[0].start_time,
                    'end_time': current_group[-1].end_time
                })
            
            # Start new group
            current_group = [prompt]
            current_duration = duration
        else:
            # Add to current group
            current_group.append(prompt)
            current_duration += duration
    
    # Don't forget the last group
    if current_group:
        segments.append({
            'id': str(uuid.uuid4()),
            'index': len(segments),
            'prompts': current_group,
            'total_duration': current_duration,
            'start_time': current_group[0].start_time,
            'end_time': current_group[-1].end_time
        })
    
    return segments


def generate_segment_prompt(segment: dict, characters: list) -> str:
    """Generate a combined prompt for a segment"""
    if not segment['prompts']:
        return ""

    prompt_parts = []

    # Add character context at the top
    if characters:
        char_names = [c.name for c in characters if c.name]
        if char_names:
            prompt_parts.append(f"Characters: {', '.join(char_names)}")

    # Add timing info
    prompt_parts.append(f"[{format_timestamp(segment['start_time'])} - {format_timestamp(segment['end_time'])}]")

    return "\n".join(prompt_parts)


def get_shot_prompts_text(segment: dict) -> list:
    """Get individual shot prompts for a segment as a list"""
    prompts = []
    shot_list = segment.get('prompts', [])
    for i, p in enumerate(shot_list):
        # Support both new structure and legacy
        continuous_action = p.get('continuous_action', p.get('prompt', ''))
        opening_frame = p.get('opening_frame', '')
        end_state = p.get('end_state', '')
        camera = p.get('camera', p.get('scene_type', ''))
        space = p.get('space', '')
        time_atmosphere = p.get('time_atmosphere', '')
        characters_in_shot = p.get('characters_in_shot', [])
        transition = p.get('transition', '')
        
        prompts.append({
            'index': i + 1,
            'start_time': p.get('start_time', 0),
            'end_time': p.get('end_time', 0),
            'duration': p.get('end_time', 0) - p.get('start_time', 0),
            'prompt': p.get('prompt', ''),
            'continuous_action': continuous_action,
            'opening_frame': opening_frame,
            'end_state': end_state,
            'camera': camera,
            'space': space,
            'time_atmosphere': time_atmosphere,
            'characters_in_shot': characters_in_shot,
            'transition': transition
        })
    return prompts


def render_shot_segmentation_page():
    """Render the shot segmentation page"""

    current_task = TaskManager.get_current_task()

    if not current_task:
        st.error("请先创建或加载任务")
        if st.button("🏠 返回主页"):
            st.switch_page("main.py")
        return

    if not current_task.source_video:
        st.warning("⚠️ 请先在【视频上传】页面上传视频")
        if st.button("📹 前往上传"):
            st.switch_page("pages/1_📹_视频上传.py")
        return

    # Check if analysis is complete
    analysis_complete = current_task.status in [
        TaskStatus.ANALYSIS_COMPLETE.value,
        TaskStatus.PROMPTS_MODIFIED.value,
        TaskStatus.GENERATING.value,
        TaskStatus.GENERATION_COMPLETE.value
    ]

    if not analysis_complete:
        st.warning("⏳ 请先完成视频分析")
        if st.button("📊 前往分析"):
            st.switch_page("pages/1_📹_视频上传.py")
        return

    # Header with back button
    col_back, col_title = st.columns([1, 4])
    with col_back:
        if st.button("🏠 返回", use_container_width=True):
            st.switch_page("main.py")
    with col_title:
        st.markdown('<h2 class="section-header">🎬 步骤 3: 镜头拆分</h2>', unsafe_allow_html=True)

    # Info cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总镜头数", len(current_task.scene_prompts) if current_task.scene_prompts else 0)
    with col2:
        total_duration = sum(get_duration_from_prompt(p) for p in current_task.scene_prompts) if current_task.scene_prompts else 0
        st.metric("总时长", f"{total_duration:.1f}s")
    with col3:
        st.metric("子视频数", len(current_task.shot_segments) if current_task.shot_segments else 0)
    with col4:
        st.metric("人物数", len(current_task.character_keyframes) if current_task.character_keyframes else 0)

    st.markdown("---")

    if not current_task.scene_prompts:
        st.markdown("""
        <div class="empty-state">
            <h3 style="color: #F8FAFC;">🔍 暂无镜头数据</h3>
            <p style="color: #94A3B8; margin-top: 1rem;">
                请在【视频上传】页面点击「开始分析」或「测试数据」来提取镜头信息
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    # Settings
    st.markdown("### ⚙️ 拆分设置")

    col_set1, col_set2 = st.columns([1, 3])
    with col_set1:
        max_duration = st.number_input(
            "最大子视频时长（秒）",
            min_value=5,
            max_value=60,
            value=15,
            step=5,
            help="每个子视频片段的最大时长，超过则拆分为多个片段"
        )

    # Generate segments button
    if st.button("🔄 重新拆分", type="primary"):
        # Generate segments
        segments = segment_shots_into_groups(current_task.scene_prompts, max_duration=max_duration)
        
        # Store segments - convert prompts back to dict for JSON serialization
        current_task.shot_segments = [
            {
                'id': seg['id'],
                'index': seg['index'],
                'total_duration': seg['total_duration'],
                'start_time': seg['start_time'],
                'end_time': seg['end_time'],
                'prompt_count': len(seg['prompts']),
                'character_context': generate_segment_prompt(seg, current_task.character_keyframes),
                'prompts': [
                    {
                        'id': p.id,
                        'start_time': p.start_time,
                        'end_time': p.end_time,
                        'prompt': p.prompt,
                        'scene_type': p.scene_type,
                        'continuous_action': p.continuous_action,
                        'space': p.space,
                        'time_atmosphere': p.time_atmosphere,
                        'camera': p.camera,
                        'characters_in_shot': [{'name': c.name, 'pose': c.pose, 'position': c.position} for c in p.characters_in_shot] if p.characters_in_shot else [],
                        'transition': p.transition,
                        'opening_frame': p.opening_frame,
                        'end_state': p.end_state
                    }
                    for p in seg['prompts']
                ]
            }
            for seg in segments
        ]
        
        TaskManager.save_task(current_task)
        st.success(f"✅ 已拆分为 {len(segments)} 个子视频片段")
        st.rerun()

    st.markdown("---")

    # Display segments
    st.markdown("### 📹 子视频片段预览")

    segments = current_task.shot_segments
    
    if not segments:
        st.info("点击「重新拆分」按钮来生成子视频片段")
    else:
        # Summary
        st.markdown(f"共 **{len(segments)}** 个子视频片段")
        
        # Create tabs for each segment
        tabs = st.tabs([f"📹 片段 {i+1} ({format_timestamp(seg['start_time'])}-{format_timestamp(seg['end_time'])})" 
                       for i, seg in enumerate(segments)])
        
        for i, (tab, seg) in enumerate(zip(tabs, segments)):
            with tab:
                # Segment info
                col_info1, col_info2, col_info3, col_info4 = st.columns(4)
                with col_info1:
                    st.metric("时长", f"{seg['total_duration']:.1f}s")
                with col_info2:
                    shot_count = seg.get('prompt_count', len(seg.get('prompts', [])))
                    st.metric("包含镜头", shot_count)
                with col_info3:
                    st.metric("时间范围", f"{format_timestamp(seg['start_time'])} - {format_timestamp(seg['end_time'])}")
                with col_info4:
                    # Get all unique characters in this segment
                    all_chars = set()
                    for p in seg.get('prompts', []):
                        for c in p.get('characters_in_shot', []):
                            if c.get('name'):
                                all_chars.add(c['name'])
                    st.metric("角色", ", ".join(sorted(all_chars)) if all_chars else "-")
                
                st.markdown("---")
                
                # Combined editable prompt
                st.markdown("#### 📝 合并提示词")
                
                # Build the combined text from all shots - single line per shot
                combined_text_lines = []
                for shot in get_shot_prompts_text(seg):
                    time_range = f"{format_timestamp(shot['start_time'])}-{format_timestamp(shot['end_time'])}"
                    
                    # Build single line with all info
                    parts = [f"{time_range}"]
                    if shot.get('camera'):
                        parts.append(f"镜头:{shot['camera']}")
                    if shot.get('space'):
                        parts.append(f"空间:{shot['space']}")
                    if shot.get('time_atmosphere'):
                        parts.append(f"氛围:{shot['time_atmosphere']}")
                    if shot.get('opening_frame'):
                        parts.append(f"开场:{shot['opening_frame']}")
                    if shot.get('continuous_action'):
                        parts.append(f"动作:{shot['continuous_action']}")
                    if shot.get('end_state'):
                        parts.append(f"结尾:{shot['end_state']}")
                    
                    combined_text_lines.append(" ".join(parts))
                
                combined_text = "\n".join(combined_text_lines)
                
                prompt_text = st.text_area(
                    "提示词（可编辑）",
                    value=combined_text,
                    height=min(300, 50 + len(combined_text_lines) * 30),
                    key=f"segment_prompt_{seg['id']}",
                    label_visibility="collapsed"
                )
        
        # Export section
        st.markdown("### 📤 导出")
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            if st.button("📋 复制所有提示词", use_container_width=True):
                export_lines = []
                for i, seg in enumerate(segments):
                    export_lines.append(f"=== 子视频 {i+1} ({format_timestamp(seg['start_time'])}-{format_timestamp(seg['end_time'])}) ===")
                    if seg.get('character_context'):
                        export_lines.append(seg['character_context'])
                    export_lines.append("镜头:")
                    for shot in get_shot_prompts_text(seg):
                        time_range = f"{format_timestamp(shot['start_time'])}-{format_timestamp(shot['end_time'])}"
                        parts = [f"{time_range}"]
                        if shot.get('camera'):
                            parts.append(f"镜头:{shot['camera']}")
                        if shot.get('space'):
                            parts.append(f"空间:{shot['space']}")
                        if shot.get('time_atmosphere'):
                            parts.append(f"氛围:{shot['time_atmosphere']}")
                        if shot.get('opening_frame'):
                            parts.append(f"开场:{shot['opening_frame']}")
                        if shot.get('continuous_action'):
                            parts.append(f"动作:{shot['continuous_action']}")
                        if shot.get('end_state'):
                            parts.append(f"结尾:{shot['end_state']}")
                        export_lines.append(" ".join(parts))
                    export_lines.append("")
                all_prompts = "\n".join(export_lines)
                st.code(all_prompts, language=None)
                st.success("提示词已生成，请复制上方内容")
        
        with col_exp2:
            if st.button("💾 保存到任务", use_container_width=True):
                TaskManager.save_task(current_task)
                st.success("✅ 已保存到任务")

        st.markdown("---")

        # Navigation
        st.markdown("### 📍 导航")
        col_nav1, col_nav2 = st.columns(2)
        with col_nav1:
            if st.button("👤 返回人物分析", use_container_width=True):
                st.switch_page("pages/2_👤_人物分析.py")
        with col_nav2:
            if st.button("✨ 前往视频生成", use_container_width=True):
                st.switch_page("pages/4_✨_视频生成.py")


# Run page
if __name__ == "__main__":
    render_shot_segmentation_page()
