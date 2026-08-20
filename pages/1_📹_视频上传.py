"""Page 1: Video Upload and AI Analysis"""

import streamlit as st
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules import Config, TaskManager, TaskStatus, AIInterface, auto_segment_task
from modules.data_models import SourceVideo
from modules.ai_interface import parse_ai_json_response, parse_duration, ScenePrompt, CharacterInShot
from modules.video_utils import extract_frame_from_timestamp_str
import uuid


def format_duration(seconds: float) -> str:
    """Format duration in seconds to mm:ss"""
    if seconds <= 0:
        return "00:00"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def format_file_size(size_bytes: int) -> str:
    """Format file size to human readable"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def render_video_upload_page():
    """Render the video upload page"""

    current_task = TaskManager.get_current_task()

    if not current_task:
        st.error("请先创建或加载任务")
        if st.button("🏠 返回主页"):
            st.switch_page("main.py")
        return

    # Header with back button
    col_back, col_title = st.columns([1, 4])
    with col_back:
        if st.button("🏠 返回", use_container_width=True):
            st.switch_page("main.py")
    with col_title:
        st.markdown('<h2 class="section-header">📹 步骤 1: 上传视频</h2>', unsafe_allow_html=True)

    # Task status display
    status_display = {
        TaskStatus.CREATED.value: ("⚪ 待处理", "info"),
        TaskStatus.VIDEO_UPLOADED.value: ("🔵 已上传", "info"),
        TaskStatus.ANALYZING.value: ("🟡 分析中...", "warning"),
        TaskStatus.ANALYSIS_COMPLETE.value: ("🟢 分析完成", "success"),
        TaskStatus.ERROR.value: ("🔴 错误", "error"),
    }

    status_text, status_type = status_display.get(
        current_task.status,
        ("⚪ 待处理", "info")
    )

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        st.metric("任务ID", current_task.task_id[:8] + "...")
    with col2:
        st.metric("状态", status_text)
    with col3:
        if current_task.source_video:
            st.metric("视频", Path(current_task.source_video.path).name)

    st.markdown("---")

    # Two column layout
    col_left, col_right = st.columns([1, 1])

    # Check if analysis is already complete
    analysis_complete = current_task.status in [
        TaskStatus.ANALYSIS_COMPLETE.value,
        TaskStatus.PROMPTS_MODIFIED.value,
        TaskStatus.GENERATING.value,
        TaskStatus.GENERATION_COMPLETE.value
    ]

    with col_left:
        st.markdown("### 🎬 上传视频文件")

        if analysis_complete:
            # Show video info, disable uploader
            if current_task.source_video:
                st.success(f"📹 {Path(current_task.source_video.path).name}")
                st.info("分析已完成，如需更换视频请新建任务")
            else:
                st.info("尚未上传视频")
        else:
            # File uploader
            uploaded_file = st.file_uploader(
                "选择视频文件",
                type=['mp4', 'avi', 'mov', 'mkv', 'webm'],
                help="支持 mp4, avi, mov, mkv, webm 格式",
                key="video_uploader"
            )

            if uploaded_file is not None:
                # Save uploaded file
                source_dir = Config.get_source_dir(current_task.task_id)
                video_path = source_dir / uploaded_file.name

                # Write file
                with open(video_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # Get file size
                file_size = uploaded_file.size

                # Update task with video info
                current_task.source_video = SourceVideo(
                    path=str(video_path),
                    file_size=file_size
                )
                current_task.update_status(TaskStatus.VIDEO_UPLOADED)
                TaskManager.save_task(current_task)

                st.success(f"✅ 视频已上传: {uploaded_file.name}")
                st.info(f"📦 文件大小: {format_file_size(file_size)}")

    with col_right:
        if current_task.source_video:
            video_path = Path(current_task.source_video.path)

            if video_path.exists():
                st.markdown("### ▶️ 视频预览")

                # Display video
                st.video(str(video_path))

                # Video info
                if current_task.source_video.duration > 0:
                    st.markdown(f"""
                    <div style="color: #94A3B8; font-size: 0.875rem; margin-top: 0.5rem;">
                        <span>⏱️ 时长: {format_duration(current_task.source_video.duration)}</span>
                        <span style="margin-left: 1rem;">📐 分辨率: {current_task.source_video.width}x{current_task.source_video.height}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("⚠️ 视频文件不存在")
        else:
            st.info("👆 请先上传视频文件")

    st.markdown("---")

    # Analysis section
    st.markdown("### 🔍 AI 视频分析")

    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])

    with col_btn1:
        # Disable button if no video, analyzing, or analysis already complete
        btn_disabled = (
            current_task.source_video is None
            or current_task.status == TaskStatus.ANALYZING.value
            or analysis_complete
        )
        analyze_clicked = st.button(
            "🚀 开始分析",
            type="primary",
            use_container_width=True,
            disabled=btn_disabled
        )

    with col_btn2:
        test_btn_disabled = analysis_complete
        test_clicked = st.button(
            "🧪 测试数据",
            use_container_width=True,
            disabled=test_btn_disabled,
            help="使用测试数据模拟AI分析"
        )

    # Only show analyze button area if not yet analyzed
    if not analysis_complete:
        # Analyze button logic
        if analyze_clicked and current_task.source_video:
            current_task.update_status(TaskStatus.ANALYZING)
            TaskManager.save_task(current_task)

            # Progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()

            try:
                status_text.markdown("🔄 正在上传视频到AI服务...")
                progress_bar.progress(10)
                time.sleep(0.5)

                # Call AI interface
                result = AIInterface.analyze_video(
                    current_task.source_video.path,
                    current_task.task_id
                )

                progress_bar.progress(80)

                if result.success:
                    # Update task with results
                    if result.character_keyframes:
                        current_task.character_keyframes = result.character_keyframes
                    if result.scene_prompts:
                        current_task.scene_prompts = result.scene_prompts
                    # Store AI analysis results
                    current_task.ai_analysis_result = result.raw_result
                    current_task.ai_style = result.ai_style
                    current_task.ai_scene = result.ai_scene

                    current_task.update_status(TaskStatus.ANALYSIS_COMPLETE)
                    TaskManager.save_task(current_task)

                    progress_bar.progress(100)
                    status_text.success(f"✅ {result.message}")
                    _auto_segment(current_task, status_text)
                    st.rerun()
                else:
                    current_task.error_message = result.error
                    current_task.update_status(TaskStatus.ERROR)
                    TaskManager.save_task(current_task)
                    progress_bar.progress(0)
                    status_text.error(f"❌ 分析失败: {result.error}")

            except Exception as e:
                current_task.error_message = str(e)
                current_task.update_status(TaskStatus.ERROR)
                TaskManager.save_task(current_task)
                progress_bar.progress(0)
                status_text.error(f"❌ 发生错误: {str(e)}")

        # Test data button logic
        if test_clicked:
            try:
                # Read test data file
                test_file_path = Path(__file__).parent.parent / "modules" / "test_ai_response.txt"
                with open(test_file_path, 'r', encoding='utf-8') as f:
                    test_result = f.read()

                # Parse the test data
                characters, style, scene, parsed_data = parse_ai_json_response(test_result)

                # Parse scene_prompts
                scene_prompts = []
                shots_data = parsed_data.get('shots', [])
                cumulative_time = 0.0

                for idx, shot_data in enumerate(shots_data):
                    duration = parse_duration(shot_data.get('time', '0'))
                    
                    # Parse characters in shot
                    chars_in_shot = []
                    for char_data in shot_data.get('characters_in_shot', []):
                        chars_in_shot.append(CharacterInShot(
                            name=char_data.get('name', ''),
                            pose=char_data.get('pose', ''),
                            position=char_data.get('position', '')
                        ))
                    
                    prompt_parts = []
                    if shot_data.get('opening_frame'):
                        prompt_parts.append(f"开场: {shot_data['opening_frame']}")
                    if shot_data.get('continuous_action'):
                        prompt_parts.append(f"动作: {shot_data['continuous_action']}")
                    if shot_data.get('end_state'):
                        prompt_parts.append(f"结尾: {shot_data['end_state']}")
                    if shot_data.get('camera'):
                        prompt_parts.append(f"镜头: {shot_data['camera']}")

                    scene_prompt = ScenePrompt(
                        id=str(uuid.uuid4()),
                        start_time=cumulative_time,
                        end_time=cumulative_time + duration,
                        continuous_action=shot_data.get('continuous_action', ''),
                        space=shot_data.get('space', ''),
                        time_atmosphere=shot_data.get('time_atmosphere', ''),
                        camera=shot_data.get('camera', ''),
                        characters_in_shot=chars_in_shot,
                        transition=shot_data.get('transition', ''),
                        opening_frame=shot_data.get('opening_frame', ''),
                        end_state=shot_data.get('end_state', ''),
                        prompt="; ".join(prompt_parts) if prompt_parts else shot_data.get('opening_frame', ''),
                        scene_type=shot_data.get('camera', '')
                    )
                    scene_prompts.append(scene_prompt)
                    cumulative_time += duration

                # Extract best frame images for test data as well
                video_path = current_task.source_video.path if current_task.source_video else None
                if video_path:
                    task_dir = Config.get_task_dir(current_task.task_id)
                    for char in characters:
                        if char.best_frame:
                            char_dir = task_dir / 'characters' / char.name
                            frame_result = extract_frame_from_timestamp_str(
                                video_path=video_path,
                                timestamp_str=char.best_frame,
                                output_dir=str(char_dir),
                                filename_prefix=f"best_frame_{char.name}"
                            )
                            if frame_result.success:
                                char.best_frame_image_path = frame_result.image_path

                # Update task
                current_task.character_keyframes = characters
                current_task.scene_prompts = scene_prompts
                current_task.ai_analysis_result = test_result
                current_task.ai_style = style
                current_task.ai_scene = scene
                current_task.update_status(TaskStatus.ANALYSIS_COMPLETE)
                TaskManager.save_task(current_task)

                st.success(f"✅ 测试数据加载完成：{len(characters)}个角色，{len(scene_prompts)}个镜头")
                _auto_segment(current_task, None)
                st.rerun()

            except Exception as e:
                st.error(f"� 测试数据加载失败: {str(e)}")


def _auto_segment(task, status_text) -> None:
    """Run auto shot segmentation and surface the result in the UI."""
    try:
        segment_count = auto_segment_task(task)
        if segment_count > 0:
            TaskManager.save_task(task)
            msg = f"🎬 已自动拆分为 {segment_count} 个子视频片段"
            if status_text is not None:
                status_text.info(msg)
            else:
                st.info(msg)
    except Exception as e:
        err = f"⚠️ 自动拆分镜头失败: {e}"
        if status_text is not None:
            status_text.warning(err)
        else:
            st.warning(err)

# Run page
if __name__ == "__main__":
    render_video_upload_page()
