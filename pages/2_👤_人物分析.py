"""Page 2: Character Keyframes and Editable Prompts"""

import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules import Config, TaskManager, TaskStatus
from modules.ai_image import generate_character_three_view, build_three_view_prompt


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
        st.metric("人物数量", kf_count if kf_count > 0 else "暂无")
    with col3:
        analyzed = "✅ 已分析" if current_task.status in [
            TaskStatus.ANALYSIS_COMPLETE.value,
            TaskStatus.PROMPTS_MODIFIED.value,
            TaskStatus.GENERATING.value,
            TaskStatus.GENERATION_COMPLETE.value
        ] else "⏳ 待分析"
        st.metric("分析状态", analyzed)

    # Display style and scene info
    if current_task.ai_style or current_task.ai_scene:
        with st.expander("📋 视频概览"):
            if current_task.ai_style:
                st.markdown(f"**🎨 画面风格:** {current_task.ai_style}")
            if current_task.ai_scene:
                st.markdown(f"**🏠 场景:** {current_task.ai_scene}")

    st.markdown("---")

    if not current_task.character_keyframes:
        st.markdown("""
        <div class="empty-state">
            <h3 style="color: #F8FAFC;">🔍 暂无人物信息</h3>
            <p style="color: #94A3B8; margin-top: 1rem;">
                请在【视频上传】页面点击「开始分析」来提取人物信息
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("### 🎭 角色信息")
        st.markdown("AI分析的角色信息，按角色ID排序显示。")
        st.markdown("---")

        # Sort characters by character_id (which is the AI's character id)
        sorted_characters = sorted(current_task.character_keyframes, key=lambda x: x.character_id)

        # Display characters in a grid
        for idx, kf in enumerate(sorted_characters):
            with st.container():
                # Character header card
                st.markdown(f"""
                <div class="keyframe-card">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
                        <div style="display: flex; align-items: center; gap: 1rem;">
                            <span style="background: #6366F1; color: white; padding: 0.25rem 0.75rem; border-radius: 9999px; font-weight: 600;">
                                角色 {idx + 1}
                            </span>
                            <span style="color: #F8FAFC; font-size: 1.1rem; font-weight: 600;">
                                {kf.name if kf.name else f'角色 {kf.character_id}'}
                            </span>
                        </div>
                        <span style="color: #94A3B8; font-size: 0.875rem;">
                            ID: {kf.character_id}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Character info
                with st.container():
                    st.markdown("#### 📝 角色详情")

                    # Display character name prominently
                    if kf.name:
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #6366F1, #8B5CF6); color: white; padding: 0.75rem 1rem; border-radius: 8px; margin-bottom: 1rem; text-align: center; font-size: 1.1rem; font-weight: 600;">
                            {kf.name}
                        </div>
                        """, unsafe_allow_html=True)

                    # Best frame timestamp
                    if kf.best_frame:
                        st.markdown(f"""
                        <div style="color: #94A3B8; font-size: 0.875rem; margin-bottom: 0.5rem;">
                            <strong style="color: #22C55E;">✨ 最佳展示帧:</strong> {kf.best_frame}
                        </div>
                        """, unsafe_allow_html=True)

                    # Two-column layout: Best frame | Three view
                    col_best, col_three = st.columns(2)

                    with col_best:
                        # Best frame image
                        st.markdown("**🎬 最佳展示帧**")
                        if kf.best_frame_image_path and Path(kf.best_frame_image_path).exists():
                            try:
                                st.image(
                                    kf.best_frame_image_path,
                                    caption=f"{kf.name} 最佳展示帧",
                                    width=300
                                )
                            except Exception as e:
                                st.error(f"❌ 无法加载最佳帧图片: {str(e)}")
                        elif kf.best_frame:
                            st.markdown("""
                            <div style="background: #374151; color: #F87171; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; text-align: center;">
                                ⚠️ 最佳帧图片不可用
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.info("暂无最佳展示帧信息")

                    with col_three:
                        st.markdown("**🎭 三视图**")

                        # Initialize session state for this character's selected index
                        three_view_key = f"three_view_selected_{kf.id}"
                        if three_view_key not in st.session_state:
                            st.session_state[three_view_key] = kf.selected_three_view_index

                        # Generate button
                        generate_key = f"generate_{kf.id}"
                        if st.button("🖼️ 生成三视图", key=generate_key, use_container_width=True):
                            if kf.best_frame_image_path and Path(kf.best_frame_image_path).exists():
                                # Build prompt
                                prompt = build_three_view_prompt(
                                    character_name=kf.name,
                                    character_description=kf.character_description,
                                    facial_features=kf.facial_features,
                                    costume=kf.costume
                                )

                                # Output directory
                                task_dir = Config.get_task_dir(current_task.task_id)
                                output_dir = str(task_dir / 'characters' / kf.name)

                                # Generate three view
                                with st.spinner("正在生成三视图..."):
                                    result = generate_character_three_view(
                                        reference_image_path=kf.best_frame_image_path,
                                        prompt=prompt,
                                        output_dir=output_dir,
                                        character_name=kf.name
                                    )

                                if result.success:
                                    # Add to three view images list
                                    kf.three_view_images.append(result.image_path)
                                    # Set as selected
                                    kf.selected_three_view_index = len(kf.three_view_images) - 1
                                    st.session_state[three_view_key] = kf.selected_three_view_index
                                    TaskManager.save_task(current_task)
                                    st.success("✅ 三视图生成成功！")
                                    st.rerun()
                                else:
                                    st.error(f"❌ 生成失败: {result.error_message}")
                            else:
                                st.error("❌ 最佳展示帧图片不可用，无法生成三视图")

                        st.markdown("---")

                        # Display three view images
                        if kf.three_view_images:
                            # Show image selector if multiple images
                            if len(kf.three_view_images) > 1:
                                st.markdown(f"已生成 {len(kf.three_view_images)} 个三视图，选择一个作为当前版本:")

                                # Create radio options
                                options = [f"版本 {i+1}" for i in range(len(kf.three_view_images))]
                                selected = st.radio(
                                    "选择三视图版本",
                                    options=options,
                                    index=st.session_state[three_view_key] if st.session_state[three_view_key] >= 0 else 0,
                                    key=f"radio_{kf.id}",
                                    label_visibility="collapsed"
                                )

                                selected_index = options.index(selected)
                                if selected_index != st.session_state[three_view_key]:
                                    kf.selected_three_view_index = selected_index
                                    st.session_state[three_view_key] = selected_index
                                    TaskManager.save_task(current_task)

                                display_index = selected_index
                            else:
                                display_index = 0

                            # Display the selected three view image
                            image_path = kf.three_view_images[display_index]
                            if Path(image_path).exists():
                                st.image(image_path, caption=f"三视图 - 版本 {display_index + 1}", width=350)
                            else:
                                st.error(f"❌ 图片文件不存在: {image_path}")
                        else:
                            st.markdown("""
                            <div style="background: #1E293B; border: 2px dashed #475569; color: #94A3B8; padding: 2rem; border-radius: 8px; margin: 0.5rem 0; text-align: center;">
                                <p>点击上方「生成三视图」按钮创建角色的三视图</p>
                                <p style="font-size: 0.875rem; margin-top: 0.5rem;">基于最佳展示帧和角色描述生成</p>
                            </div>
                            """, unsafe_allow_html=True)

                    # Merged editable content for description, facial features, and costume
                    combined_content = ""
                    parts = []
                    if kf.character_description:
                        parts.append(f"【描述】{kf.character_description}")
                    if kf.facial_features:
                        parts.append(f"【面部特征】{kf.facial_features}")
                    if kf.costume:
                        parts.append(f"【服饰】{kf.costume}")
                    combined_content = "\n\n".join(parts)

                    new_combined = st.text_area(
                        "角色详情（可编辑）",
                        value=combined_content,
                        height=200,
                        key=f"combined_{kf.id}",
                        help="合并的角色描述信息，可编辑"
                    )

                    # Show timestamp info
                    if kf.timestamp > 0:
                        st.caption(f"⏱️ 帧位置: {format_timestamp(kf.timestamp)}")

                    # Update on change
                    if new_combined != combined_content:
                        # Parse and update individual fields
                        lines = new_combined.split("\n\n")
                        for line in lines:
                            if line.startswith("【描述】"):
                                kf.character_description = line[4:].strip()
                            elif line.startswith("【面部特征】"):
                                kf.facial_features = line[6:].strip()
                            elif line.startswith("【服饰】"):
                                kf.costume = line[4:].strip()
                        # Also update prompt
                        kf.prompt = kf.character_description
                        if current_task.status != TaskStatus.PROMPTS_MODIFIED.value:
                            current_task.update_status(TaskStatus.PROMPTS_MODIFIED)
                        TaskManager.save_task(current_task)
                        st.toast("✅ 角色详情已保存", icon="💾")

                st.markdown("---")


# Run page
if __name__ == "__main__":
    render_character_page()
