"""Page 3: Scene/Shots Analysis with Editable Prompts"""

import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules import Config, TaskManager, TaskStatus


def render_scene_page():
    """Render the scene/shots analysis page"""

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
        st.markdown('<h2 class="section-header">🎬 步骤 3: 镜头分析</h2>', unsafe_allow_html=True)

    # Info cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("视频文件", Path(current_task.source_video.path).name)
    with col2:
        scene_count = len(current_task.scene_prompts)
        st.metric("场景镜头", scene_count if scene_count > 0 else "暂无")
    with col3:
        if current_task.source_video.duration > 0:
            st.metric("总时长", f"{int(current_task.source_video.duration)}s")

    st.markdown("---")

    if not current_task.scene_prompts:
        st.markdown("""
        <div class="empty-state">
            <h3 style="color: #F8FAFC;">🔍 暂无场景镜头</h3>
            <p style="color: #94A3B8; margin-top: 1rem;">
                请在【视频上传】页面点击「开始分析」或「添加测试数据」来提取场景信息
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("### 🎥 场景提示词")
        st.markdown("每个场景的提示词可以修改，修改将自动保存。")

        # Scene cards
        for idx, scene in enumerate(current_task.scene_prompts):
            with st.container():
                st.markdown(f"""
                <div class="keyframe-card">
                    <div style="display: flex; align-items: center; gap: 1rem;">
                        <span style="background: linear-gradient(135deg, #6366F1, #8B5CF6); color: white; padding: 0.25rem 0.75rem; border-radius: 9999px; font-weight: 600;">
                            镜头 {idx + 1}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Prompt editor only
                new_prompt = st.text_area(
                    "场景提示词",
                    value=scene.prompt,
                    height=100,
                    key=f"scene_prompt_{scene.id}",
                    help="修改场景描述提示词"
                )

                # Update prompt on change
                if new_prompt != scene.prompt:
                    current_task.update_scene_prompt(scene.id, new_prompt)
                    if current_task.status != TaskStatus.PROMPTS_MODIFIED.value:
                        current_task.update_status(TaskStatus.PROMPTS_MODIFIED)
                    TaskManager.save_task(current_task)
                    st.toast("✅ 已保存", icon="💾")

                st.markdown("---")


# Run page
if __name__ == "__main__":
    render_scene_page()
