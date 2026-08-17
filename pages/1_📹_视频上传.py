"""Page 1: Video Upload and AI Analysis"""

import streamlit as st
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules import Config, TaskManager, TaskStatus, AIInterface
from modules.data_models import SourceVideo


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
                status_text.markdown("🔄 正在分析视频..")
                progress_bar.progress(20)
                time.sleep(0.5)


                # Call AI interface (placeholder)
                result = AIInterface.analyze_video(
                    current_task.source_video.path,
                    current_task.task_id
                )

                progress_bar.progress(100)

                if result.success:
                    # Update task with results
                    if result.character_keyframes:
                        current_task.character_keyframes = result.character_keyframes
                    if result.scene_prompts:
                        current_task.scene_prompts = result.scene_prompts

                    current_task.update_status(TaskStatus.ANALYSIS_COMPLETE)
                    TaskManager.save_task(current_task)

                    status_text.success("✅ 分析完成!")
                    st.rerun()
                else:
                    current_task.error_message = result.error
                    current_task.update_status(TaskStatus.ERROR)
                    TaskManager.save_task(current_task)
                    status_text.error(f"❌ 分析失败: {result.error}")

            except Exception as e:
                current_task.error_message = str(e)
                current_task.update_status(TaskStatus.ERROR)
                TaskManager.save_task(current_task)
                status_text.error(f"❌ 发生错误: {str(e)}")

        with col_btn2:
            # Add demo data for testing
            if st.button("📋 添加测试数据", use_container_width=True, help="添加演示数据以便测试"):
                from modules.data_models import CharacterKeyframe, ScenePrompt
                import uuid

                # Create demo keyframes
                current_task.character_keyframes = [
                    CharacterKeyframe(
                        id=str(uuid.uuid4()),
                        frame_index=1,
                        timestamp=2.5,
                        image_path="",
                        prompt="A young woman with long black hair wearing a red dress, standing in a sunlit room",
                        character_description="Young woman, late 20s, long black hair, red elegant dress",
                        confidence=0.92
                    ),
                    CharacterKeyframe(
                        id=str(uuid.uuid4()),
                        frame_index=2,
                        timestamp=8.3,
                        image_path="",
                        prompt="An elderly man with gray beard wearing casual shirt, sitting on a wooden chair",
                        character_description="Elderly man, 60s, gray beard, blue casual shirt",
                        confidence=0.88
                    ),
                    CharacterKeyframe(
                        id=str(uuid.uuid4()),
                        frame_index=3,
                        timestamp=15.7,
                        image_path="",
                        prompt="A child with blonde curly hair wearing a yellow t-shirt, playing with a ball",
                        character_description="Child, 5-6 years old, blonde curly hair, yellow t-shirt",
                        confidence=0.85
                    ),
                ]

                # Create demo scene prompts
                current_task.scene_prompts = [
                    ScenePrompt(
                        id=str(uuid.uuid4()),
                        start_time=0.0,
                        end_time=5.0,
                        prompt="Interior living room with large windows, warm afternoon sunlight streaming in, cozy furniture arrangement with vintage wooden coffee table",
                        scene_type="interior",
                        camera_movement="slow pan",
                        lighting="natural warm"
                    ),
                    ScenePrompt(
                        id=str(uuid.uuid4()),
                        start_time=5.0,
                        end_time=12.0,
                        prompt="Close-up shot of two characters having an emotional conversation, soft bokeh background, intimate atmosphere",
                        scene_type="close-up",
                        camera_movement="static",
                        lighting="studio soft"
                    ),
                    ScenePrompt(
                        id=str(uuid.uuid4()),
                        start_time=12.0,
                        end_time=20.0,
                        prompt="Wide establishing shot of a garden with colorful flowers, butterflies flying, peaceful morning atmosphere",
                        scene_type="establishing",
                        camera_movement="dolly forward",
                        lighting="golden hour"
                    ),
                    ScenePrompt(
                        id=str(uuid.uuid4()),
                        start_time=20.0,
                        end_time=30.0,
                        prompt="Medium shot of characters walking through a forest path, dappled sunlight through trees, magical atmosphere",
                        scene_type="action",
                        camera_movement="tracking",
                        lighting="natural filtered"
                    ),
                ]

                current_task.update_status(TaskStatus.ANALYSIS_COMPLETE)
                TaskManager.save_task(current_task)
                st.success("✅ 测试数据已添加!")
                st.rerun()

        with col_btn3:
            if current_task.character_keyframes:
                st.success(f"✅ 已提取 {len(current_task.character_keyframes)} 个人物关键帧")
            else:
                st.info("尚未提取人物关键帧")
    else:
        # Show completion status
        st.success("✅ 视频分析已完成，可前往后续页面继续操作")
        with st.expander("📊 分析结果摘要"):
            if current_task.character_keyframes:
                st.markdown(f"**👤 人物关键帧:** {len(current_task.character_keyframes)} 个")
            if current_task.scene_prompts:
                st.markdown(f"**🎬 场景镜头:** {len(current_task.scene_prompts)} 个")


# Run page
if __name__ == "__main__":
    render_video_upload_page()
