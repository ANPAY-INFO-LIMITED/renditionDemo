"""Page 4: Video Generation"""

import streamlit as st
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules import Config, TaskManager, TaskStatus, AIInterface


def count_total_prompts(task) -> dict:
    """Count prompts from character and scene analysis"""
    char_count = len(task.character_keyframes)
    scene_count = len(task.scene_prompts)
    return {"characters": char_count, "scenes": scene_count}


def render_generation_page():
    """Render the video generation page"""

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

    # Header with back button
    col_back, col_title = st.columns([1, 4])
    with col_back:
        if st.button("🏠 返回", use_container_width=True):
            st.switch_page("main.py")
    with col_title:
        st.markdown('<h2 class="section-header">✨ 步骤 4: 视频生成</h2>', unsafe_allow_html=True)

    # Info cards
    col1, col2, col3 = st.columns(3)

    prompt_counts = count_total_prompts(current_task)
    has_prompts = prompt_counts["characters"] > 0 or prompt_counts["scenes"] > 0

    with col1:
        st.metric("人物提示词", prompt_counts["characters"])
    with col2:
        st.metric("场景提示词", prompt_counts["scenes"])
    with col3:
        has_generated = current_task.generated_video is not None and current_task.generated_video.path
        st.metric("生成状态", "✅ 已生成" if has_generated else "⏳ 待生成")

    st.markdown("---")

    # Check if prompts are ready
    if not has_prompts:
        st.markdown("""
        <div class="empty-state">
            <h3 style="color: #F8FAFC;">🔍 暂无提示词</h3>
            <p style="color: #94A3B8; margin-top: 1rem;">
                请先在【视频上传】页面完成视频分析，提取人物和场景提示词
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Prompts summary
        st.markdown("### 📋 使用的提示词")

        with st.expander("👤 人物提示词预览", expanded=False):
            for idx, kf in enumerate(current_task.character_keyframes):
                st.markdown(f"**人物 {idx + 1}:** {kf.prompt}")

        with st.expander("🎬 场景提示词预览", expanded=False):
            for idx, sp in enumerate(current_task.scene_prompts):
                st.markdown(f"**镜头 {idx + 1}:** {sp.prompt}")

        st.markdown("---")

        # Generation controls
        st.markdown("### 🎬 视频生成")

        col_gen1, col_gen2, col_gen3 = st.columns([1, 1, 2])

        with col_gen1:
            generate_clicked = st.button(
                "🚀 生成视频",
                type="primary",
                use_container_width=True,
                disabled=current_task.status == TaskStatus.GENERATING.value
            )

        if generate_clicked and current_task.status != TaskStatus.GENERATING.value:
            current_task.update_status(TaskStatus.GENERATING)
            TaskManager.save_task(current_task)

            # Progress bar
            progress_bar = st.progress(0)
            status_container = st.empty()

            try:
                # Get output path
                output_dir = Config.get_output_dir(current_task.task_id)
                output_path = str(output_dir / "generated_video.mp4")

                def update_progress(progress):
                    progress_bar.progress(progress)
                    if progress < 0.3:
                        status_container.markdown("🔄 正在准备生成参数...")
                    elif progress < 0.6:
                        status_container.markdown("🔄 正在调用 AI 生成模型...")
                    elif progress < 0.9:
                        status_container.markdown("🔄 正在渲染视频帧...")
                    else:
                        status_container.markdown("🔄 正在合成最终视频...")

                # Call AI generation (placeholder)
                result = AIInterface.generate_video(
                    current_task,
                    output_path,
                    progress_callback=update_progress
                )

                progress_bar.progress(100)

                if result.success:
                    # Update task with generated video info
                    from modules.data_models import GeneratedVideo
                    from datetime import datetime

                    current_task.generated_video = GeneratedVideo(
                        path=result.video_path or output_path,
                        used_character_prompts=[kf.id for kf in current_task.character_keyframes],
                        used_scene_prompts=[sp.id for sp in current_task.scene_prompts],
                        generated_at=datetime.now().isoformat(),
                        duration=0.0  # Would be extracted from actual video
                    )
                    current_task.update_status(TaskStatus.GENERATION_COMPLETE)
                    TaskManager.save_task(current_task)

                    status_container.success("✅ 视频生成完成!")
                    st.balloons()
                    st.rerun()
                else:
                    current_task.error_message = result.error
                    current_task.update_status(TaskStatus.ERROR)
                    TaskManager.save_task(current_task)
                    status_container.error(f"❌ 生成失败: {result.error}")

            except Exception as e:
                current_task.error_message = str(e)
                current_task.update_status(TaskStatus.ERROR)
                TaskManager.save_task(current_task)
                status_container.error(f"❌ 发生错误: {str(e)}")

        with col_gen2:
            if st.button("🔄 重新生成", use_container_width=True, disabled=current_task.status == TaskStatus.GENERATING.value):
                if current_task.generated_video:
                    # Delete old generated video
                    old_path = Path(current_task.generated_video.path)
                    if old_path.exists():
                        old_path.unlink()

                    current_task.generated_video = None
                    current_task.update_status(TaskStatus.ANALYSIS_COMPLETE)
                    TaskManager.save_task(current_task)
                    st.rerun()

        with col_gen3:
            if current_task.status == TaskStatus.GENERATING.value:
                st.info("⏳ 正在生成视频中，请稍候...")
            elif has_generated:
                st.success("✅ 视频已生成完毕")

        st.markdown("---")

        # Generated video display
        if current_task.generated_video and current_task.generated_video.path:
            video_path = Path(current_task.generated_video.path)

            if video_path.exists():
                st.markdown("### 🎬 生成结果")

                # Video player
                st.video(str(video_path))

                # Video info
                if current_task.generated_video.generated_at:
                    st.markdown(f"""
                    <div style="color: #94A3B8; font-size: 0.875rem; margin-top: 1rem;">
                        <span>✅ 生成时间: {current_task.generated_video.generated_at[:19]}</span>
                    </div>
                    """, unsafe_allow_html=True)

                # Download button placeholder
                st.download_button(
                    label="📥 下载视频",
                    data=open(str(video_path), "rb").read(),
                    file_name=f"generated_{current_task.task_id[:8]}.mp4",
                    mime="video/mp4"
                )
            else:
                st.warning("⚠️ 生成的视频文件不存在，请重新生成")
        else:
            # Placeholder for generated video
            st.markdown("""
            <div class="empty-state" style="padding: 3rem;">
                <div style="font-size: 4rem; margin-bottom: 1rem;">🎬</div>
                <h3 style="color: #F8FAFC;">视频尚未生成</h3>
                <p style="color: #94A3B8; margin-top: 1rem;">
                    点击上方「生成视频」按钮开始生成
                </p>
            </div>
            """, unsafe_allow_html=True)


# Run page
if __name__ == "__main__":
    render_generation_page()
