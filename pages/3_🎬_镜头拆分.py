"""Page 3: Shot Segmentation - Split shots into sub-video prompts"""

import streamlit as st
from pathlib import Path
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules import TaskManager, TaskStatus, auto_segment_task
from modules.data_models import ScenePrompt


def format_timestamp(seconds: float) -> str:
    """Format timestamp to mm:ss"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def get_duration_from_prompt(prompt: ScenePrompt) -> float:
    """Calculate duration from scene prompt"""
    return prompt.end_time - prompt.start_time


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

    # Auto-segment on entry if scene_prompts exist but no segments yet
    if not current_task.shot_segments:
        with st.spinner("🎬 首次进入，正在自动拆分镜头..."):
            count = auto_segment_task(current_task)
        if count > 0:
            TaskManager.save_task(current_task)
            st.success(f"✅ 已自动生成 {count} 个子视频片段")
            st.rerun()

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
        # Generate segments via shared helper
        count = auto_segment_task(current_task, max_duration=max_duration)
        TaskManager.save_task(current_task)
        st.success(f"✅ 已拆分为 {count} 个子视频片段")
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
                # Read the combined prompt once (used for metrics + editor)
                combined_text = seg.get('combined_prompt', '')

                # Segment info
                col_info1, col_info2, col_info3, col_info4 = st.columns(4)
                with col_info1:
                    st.metric("时长", f"{seg['total_duration']:.1f}s")
                with col_info2:
                    if 'prompt_count' in seg:
                        shot_count = seg['prompt_count']
                    elif combined_text:
                        shot_count = combined_text.count('\n') + 1
                    else:
                        shot_count = 0
                    st.metric("包含镜头", shot_count)
                with col_info3:
                    st.metric("时间范围", f"{format_timestamp(seg['start_time'])} - {format_timestamp(seg['end_time'])}")
                with col_info4:
                    st.metric("角色", seg.get('character_context') or "-")

                st.markdown("---")

                # Combined editable prompt (single merged text)
                st.markdown("#### 📝 合并提示词")

                prompt_text = st.text_area(
                    "提示词（可编辑）",
                    value=combined_text,
                    height=min(400, 80 + (combined_text.count('\n') + 1) * 24),
                    key=f"segment_prompt_{seg['id']}",
                    label_visibility="collapsed"
                )

                # Persist edits back to the segment
                if prompt_text != combined_text:
                    seg['combined_prompt'] = prompt_text
                    current_task.shot_segments = segments
                    current_task.updated_at = datetime.now().isoformat()
                    TaskManager.save_task(current_task)


# Run page
if __name__ == "__main__":
    render_shot_segmentation_page()
