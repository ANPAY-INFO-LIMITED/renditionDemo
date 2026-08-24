"""Page 3: Shot Segmentation - Split shots into sub-video prompts"""

import streamlit as st
import os
import base64
from pathlib import Path
import sys
from datetime import datetime
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules import TaskManager, TaskStatus, auto_segment_task, Config
from modules.data_models import ScenePrompt, CharacterKeyframe
from modules.ai_createvido import generate_video_with_three_views, VideoGenerationResult


def format_timestamp(seconds: float) -> str:
    """Format timestamp to mm:ss"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def get_duration_from_prompt(prompt: ScenePrompt) -> float:
    """Calculate duration from scene prompt"""
    return prompt.end_time - prompt.start_time


def get_segment_characters(seg: dict, current_task) -> list:
    """
    获取片段中出现的角色列表
    根据片段时间范围和角色出现时间确定该片段包含哪些角色
    """
    seg_start = seg.get('start_time', 0)
    seg_end = seg.get('end_time', 0)
    
    characters_in_segment = []
    if current_task.character_keyframes:
        for char in current_task.character_keyframes:
            # 如果角色的最佳帧在该片段时间范围内，则认为该角色出现在此片段
            if char.timestamp >= seg_start and char.timestamp <= seg_end:
                characters_in_segment.append(char)
            # 也检查角色的三视图是否已生成
            elif char.three_view_images and len(char.three_view_images) > 0:
                # 如果角色有生成三视图，可能也包含在内
                characters_in_segment.append(char)
    
    # 去重
    seen = set()
    unique_chars = []
    for c in characters_in_segment:
        if c.name not in seen:
            seen.add(c.name)
            unique_chars.append(c)
    
    return unique_chars


def get_character_three_view(char: CharacterKeyframe) -> dict:
    """获取角色的三视图信息"""
    if not char.three_view_images:
        return None
    
    # 获取选定的三视图或默认第一个
    if char.selected_three_view_index >= 0 and char.selected_three_view_index < len(char.three_view_images):
        image_path = char.three_view_images[char.selected_three_view_index]
    elif char.three_view_images:
        image_path = char.three_view_images[0]
    else:
        return None
    
    return {
        "name": char.name,
        "image_path": image_path
    }


def generate_segment_video(seg: dict, current_task, task_dir: str = "") -> VideoGenerationResult:
    """
    为片段生成视频

    Args:
        seg: 片段信息
        current_task: 当前任务
        task_dir: 任务目录路径

    Returns:
        VideoGenerationResult: 生成结果
    """
    # 获取片段包含的角色
    characters = get_segment_characters(seg, current_task)

    # 获取角色三视图列表
    character_images = []
    for char in characters:
        three_view = get_character_three_view(char)
        if three_view:
            character_images.append(three_view)

    if not character_images:
        return VideoGenerationResult(
            success=False,
            error_message="该片段没有可用的角色三视图"
        )

    # 获取提示词和风格
    scene_prompt = seg.get('combined_prompt', '')
    ai_style = current_task.ai_style or ''

    return generate_video_with_three_views(
        character_images=character_images,
        scene_prompt=scene_prompt,
        ai_style=ai_style,
        ratio="9:16",
        task_dir=task_dir
    )


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
    col_back, _ = st.columns([1, 4])
    with col_back:
        if st.button("🏠 返回", use_container_width=True):
            st.switch_page("main.py")

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
                
                # 获取该片段包含的角色
                characters_in_seg = get_segment_characters(seg, current_task)

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
                    # 显示角色数量和名称
                    char_count = len(characters_in_seg)
                    char_names = ", ".join([c.name for c in characters_in_seg]) if characters_in_seg else "无"
                    st.metric("角色", f"{char_count}人")

                # 角色列单独展示
                if characters_in_seg:
                    st.markdown("#### 👥 包含角色")
                    char_cols = st.columns(len(characters_in_seg))
                    for j, char in enumerate(characters_in_seg):
                        with char_cols[j]:
                            st.markdown(f"**{char.name}**")
                            # 显示三视图
                            if char.three_view_images:
                                three_view = char.three_view_images[0] if char.selected_three_view_index < 0 else char.three_view_images[char.selected_three_view_index]
                                if os.path.exists(three_view):
                                    st.image(three_view, width=150, caption=f"三视图")
                                else:
                                    st.info("三视图未生成")
                            else:
                                st.info("未生成三视图")
                else:
                    st.info("该片段暂未检测到角色，请确保角色三视图已生成")

                st.markdown("---")

                # 视频生成区域
                st.markdown("#### 🎬 视频生成")
                
                # 初始化选中视频索引
                if 'generated_videos' not in seg:
                    seg['generated_videos'] = []
                if 'selected_video_index' not in seg:
                    seg['selected_video_index'] = -1
                
                # 显示当前已生成的视频数量
                video_count = len(seg.get('generated_videos', []))
                if video_count > 0:
                    st.markdown(f"已生成 **{video_count}** 个视频")
                else:
                    st.markdown("暂无生成的视频")
                
                # 视频生成按钮
                col_gen1, col_gen2 = st.columns([1, 3])
                with col_gen1:
                    if st.button("🎬 生成视频", key=f"generate_btn_{seg['id']}"):
                        if characters_in_seg:
                            with st.spinner("正在生成视频，请稍候..."):
                                # 创建进度条
                                progress_bar = st.progress(0)
                                status_text = st.empty()
                                
                                status_text.text("正在调用AI生成视频...")
                                progress_bar.progress(20)

                                # 获取任务目录
                                task_dir = str(Config.get_task_dir(current_task.task_id))

                                # 生成视频
                                result = generate_segment_video(seg, current_task, task_dir)

                                progress_bar.progress(80)

                                if result.success:
                                    # 保存视频信息
                                    video_info = {
                                        'task_id': result.task_id,
                                        'video_url': result.video_url,
                                        'video_path': result.video_path,  # 本地保存路径
                                        'generated_at': datetime.now().isoformat(),
                                        'character_count': len(characters_in_seg)
                                    }
                                    
                                    # 添加到视频列表
                                    if 'generated_videos' not in seg:
                                        seg['generated_videos'] = []
                                    seg['generated_videos'].append(video_info)
                                    
                                    # 自动选中新生成的视频
                                    seg['selected_video_index'] = len(seg['generated_videos']) - 1
                                    
                                    # 保存任务
                                    current_task.updated_at = datetime.now().isoformat()
                                    TaskManager.save_task(current_task)
                                    
                                    progress_bar.progress(100)
                                    status_text.text("视频生成成功!")
                                    st.success(f"✅ 视频生成成功! Task ID: {result.task_id}")
                                    st.rerun()
                                else:
                                    progress_bar.progress(100)
                                    status_text.text("视频生成失败")
                                    st.error(f"❌ {result.error_message}")
                        else:
                            st.warning("该片段没有包含角色的三视图，无法生成视频")
                
                st.markdown("---")
                
                # 视频播放和切换区域
                if seg.get('generated_videos') and len(seg['generated_videos']) > 0:
                    # 获取当前选中视频索引
                    saved_idx = seg.get('selected_video_index', 0)
                    if saved_idx < 0 or saved_idx >= len(seg['generated_videos']):
                        saved_idx = 0

                    # 片段预览标题
                    st.markdown("#### ▶️ 片段预览")

                    # 下拉选择视频
                    video_options = list(range(len(seg['generated_videos'])))
                    
                    # 使用 session_state 管理
                    select_key = f"video_select_{seg['id']}"
                    if select_key not in st.session_state:
                        st.session_state[select_key] = saved_idx
                    
                    # selectbox 使用 session_state 作为初始值
                    selected_video = st.selectbox(
                        "选择视频",
                        options=video_options,
                        format_func=lambda x: f"视频 {x+1}",
                        key=select_key
                    )
                    
                    # 检测选择变化并保存
                    if selected_video != saved_idx:
                        seg['selected_video_index'] = selected_video
                        current_task.updated_at = datetime.now().isoformat()
                        TaskManager.save_task(current_task)
                        st.rerun()

                    # 显示选中的视频
                    current_video = seg['generated_videos'][selected_video]

                    # 播放视频
                    video_path = current_video.get('video_path', '')

                    # 固定宽度容器
                    col1, col2, col3 = st.columns([2, 1, 2])
                    with col2:
                        if video_path and os.path.exists(video_path):
                            st.video(video_path)
                        else:
                            st.info("视频文件不可用")
                else:
                    st.info("点击「生成视频」按钮来创建视频")

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
