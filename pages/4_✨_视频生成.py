"""Page 4: Video Generation"""

import streamlit as st
import os
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules import Config, TaskManager, TaskStatus, concat_videos, VideoConcatResult


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

    # 初始化 session state
    if 'concat_video_generated' not in st.session_state:
        st.session_state.concat_video_generated = False

    # Header with back button
    col_back, _ = st.columns([1, 4])
    with col_back:
        if st.button("🏠 返回", use_container_width=True):
            st.switch_page("main.py")

    st.markdown("---")

    # 拼接视频功能
    st.markdown("#### 🎬 完整视频拼接")

    # 收集所有已生成且已选定的视频路径（按子片段顺序）
    video_paths_to_concat = []
    if current_task.shot_segments:
        for idx, seg in enumerate(current_task.shot_segments):
            if seg.get('generated_videos'):
                # 获取该片段选中的视频
                selected_idx = seg.get('selected_video_index', 0)
                videos = seg['generated_videos']
                if 0 <= selected_idx < len(videos):
                    video_path = videos[selected_idx].get('video_path', '')
                    if video_path and os.path.exists(video_path):
                        video_paths_to_concat.append(video_path)

    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.metric("待拼接片段数", len(video_paths_to_concat) if current_task.shot_segments else 0)
    with col_info2:
        if current_task.generated_video and current_task.generated_video.path:
            if os.path.exists(current_task.generated_video.path):
                st.metric("拼接视频", "✅ 已生成")
            else:
                st.metric("拼接视频", "⚠️ 文件不存在")
        else:
            st.metric("拼接视频", "⏳ 待生成")

    # 生成按钮
    col_btn1, col_btn2 = st.columns([1, 3])
    with col_btn1:
        if st.button("🎬 生成完整视频", type="primary", use_container_width=True):
            if not video_paths_to_concat:
                st.error("没有可拼接的视频，请先在【分镜分析】页面生成子片段视频")
            else:
                output_dir = Config.get_output_dir(current_task.task_id)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = str(output_dir / f"complete_video_{timestamp}.mp4")

                with st.spinner("正在拼接视频..."):
                    result: VideoConcatResult = concat_videos(video_paths_to_concat, output_path)

                    if result.success:
                        # 更新任务
                        from modules.data_models import GeneratedVideo
                        current_task.generated_video = GeneratedVideo(
                            path=result.output_path,
                            used_character_prompts=[],
                            used_scene_prompts=[],
                            generated_at=datetime.now().isoformat(),
                            duration=result.duration
                        )
                        current_task.updated_at = datetime.now().isoformat()
                        TaskManager.save_task(current_task)

                        st.session_state.concat_video_generated = True
                        st.success(f"✅ 视频拼接成功! 时长: {result.duration:.1f}秒")
                        st.rerun()
                    else:
                        st.error(f"❌ {result.error_message}")

    with col_btn2:
        if video_paths_to_concat:
            st.info(f"将拼接 {len(video_paths_to_concat)} 个视频片段")
        else:
            st.info("没有可拼接的视频")

    # 显示拼接后的视频
    if current_task.generated_video and current_task.generated_video.path:
        output_path = current_task.generated_video.path
        if os.path.exists(output_path):
            st.markdown("---")
            st.markdown("##### ▶️ 完整视频播放")

            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                st.video(output_path)

            if current_task.generated_video.generated_at:
                st.markdown(f"""
                <div style="color: #94A3B8; font-size: 0.875rem;">
                    生成时间: {current_task.generated_video.generated_at[:19]}
                </div>
                """, unsafe_allow_html=True)

            # 下载按钮
            with open(output_path, 'rb') as f:
                st.download_button(
                    label="📥 下载完整视频",
                    data=f,
                    file_name=f"complete_{current_task.task_id[:8]}.mp4",
                    mime="video/mp4"
                )


# Run page
if __name__ == "__main__":
    render_generation_page()
