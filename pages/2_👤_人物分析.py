"""Page 2: Character Keyframes and Editable Prompts"""

import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules import Config, TaskManager, TaskStatus


def format_timestamp(seconds: float) -> str:
    """Format timestamp to mm:ss.ms"""
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes:02d}:{secs:05.2f}"


def render_character_page():
    """Render the character analysis page"""

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
        st.markdown('<h2 class="section-header">👤 步骤 2: 人物分析</h2>', unsafe_allow_html=True)

    # Info cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("视频文件", Path(current_task.source_video.path).name)
    with col2:
        kf_count = len(current_task.character_keyframes)
        st.metric("人物关键帧", kf_count if kf_count > 0 else "暂无")
    with col3:
        analyzed = "✅ 已分析" if current_task.status in [
            TaskStatus.ANALYSIS_COMPLETE.value,
            TaskStatus.PROMPTS_MODIFIED.value,
            TaskStatus.GENERATING.value,
            TaskStatus.GENERATION_COMPLETE.value
        ] else "⏳ 待分析"
        st.metric("分析状态", analyzed)

    st.markdown("---")

    if not current_task.character_keyframes:
        st.markdown("""
        <div class="empty-state">
            <h3 style="color: #F8FAFC;">🔍 暂无人物关键帧</h3>
            <p style="color: #94A3B8; margin-top: 1rem;">
                请在【视频上传】页面点击「开始分析」或「添加测试数据」来提取人物信息
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("### 🎭 人物关键帧与提示词")
        st.markdown("每个关键帧下方可以编辑对应的提示词，修改将自动保存。")
        st.markdown("---")

        # Display keyframes in a grid
        for idx, kf in enumerate(current_task.character_keyframes):
            with st.container():
                st.markdown(f"""
                <div class="keyframe-card">
                    <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 0.5rem;">
                        <span style="background: #6366F1; color: white; padding: 0.25rem 0.75rem; border-radius: 9999px; font-weight: 600;">
                            人物 {idx + 1}
                        </span>
                        <span style="color: #94A3B8; font-size: 0.875rem;">
                            ⏱️ {format_timestamp(kf.timestamp)} | 置信度: {kf.confidence:.0%}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Two columns: image and prompt editor
                col_img, col_prompt = st.columns([1, 2])

                with col_img:
                    if kf.image_path and Path(kf.image_path).exists():
                        st.image(str(Path(kf.image_path)), width=300)
                    else:
                        # Placeholder for keyframe image
                        st.markdown(f"""
                        <div style="width: 300px; height: 170px; background: #334155; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #94A3B8;">
                            <div style="text-align: center;">
                                <div style="font-size: 3rem;">👤</div>
                                <div style="font-size: 0.875rem; margin-top: 0.5rem;">帧 #{kf.frame_index}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                with col_prompt:
                    # Character description
                    if kf.character_description:
                        st.markdown(f"""
                        <div style="color: #94A3B8; font-size: 0.875rem; margin-bottom: 0.5rem;">
                            <strong style="color: #8B5CF6;">👤 人物描述:</strong> {kf.character_description}
                        </div>
                        """, unsafe_allow_html=True)

                    # Editable prompt
                    new_prompt = st.text_area(
                        "✏️ 提示词",
                        value=kf.prompt,
                        height=120,
                        key=f"prompt_{kf.id}",
                        help="修改提示词以自定义人物描述"
                    )

                    # Update prompt on change
                    if new_prompt != kf.prompt:
                        current_task.update_keyframe_prompt(kf.id, new_prompt)
                        if current_task.status != TaskStatus.PROMPTS_MODIFIED.value:
                            current_task.update_status(TaskStatus.PROMPTS_MODIFIED)
                        TaskManager.save_task(current_task)
                        st.toast("✅ 提示词已保存", icon="💾")

                st.markdown("---")


# Run page
if __name__ == "__main__":
    render_character_page()
