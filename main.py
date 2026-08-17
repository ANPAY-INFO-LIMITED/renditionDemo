"""RenditionDemo - Video Processing with AI

Main entry point for the Streamlit application.
"""

import streamlit as st
from pathlib import Path

from modules import Config, TaskManager, TaskStatus

# Configure page
st.set_page_config(
    page_title="RenditionDemo - 视频处理工具",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --primary: #6366F1;
        --secondary: #8B5CF6;
        --bg-dark: #0F172A;
        --surface: #1E293B;
        --text-primary: #F8FAFC;
        --text-secondary: #94A3B8;
        --success: #22C55E;
        --warning: #F59E0B;
        --error: #EF4444;
        --border: #334155;
    }

    /* Page background */
    .stApp {
        background-color: var(--bg-dark);
    }

    /* Custom card styling */
    .custom-card {
        background-color: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 0.5rem 0;
    }

    /* Task card */
    .task-card {
        background-color: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        transition: all 0.2s;
    }

    .task-card:hover {
        border-color: var(--primary);
        transform: translateX(4px);
    }

    /* Button styling */
    .stButton > button {
        background-color: var(--primary);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
        transition: all 0.2s;
    }

    .stButton > button:hover {
        background-color: var(--secondary);
        transform: translateY(-1px);
    }

    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables"""
    if 'current_task' not in st.session_state:
        st.session_state['current_task'] = None
    if 'nav_to_page' not in st.session_state:
        st.session_state['nav_to_page'] = None


def get_status_display(status: str) -> tuple:
    """Get display text and color for task status"""
    status_map = {
        'created': ('⚪ 待处理', '#94A3B8'),
        'video_uploaded': ('🔵 已上传', '#6366F1'),
        'analyzing': ('🟡 分析中', '#F59E0B'),
        'analysis_complete': ('🟢 分析完成', '#22C55E'),
        'prompts_modified': ('🟣 已修改', '#8B5CF6'),
        'generating': ('🟡 生成中', '#F59E0B'),
        'generation_complete': ('🟣 生成完成', '#8B5CF6'),
        'error': ('🔴 错误', '#EF4444'),
    }
    return status_map.get(status, ('⚪ 未知', '#94A3B8'))


def render_welcome_page():
    """Render the main welcome page with task management"""

    # Page header
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="color: #F8FAFC; margin-bottom: 0.5rem; font-size: 2.5rem;">
            🎬 RenditionDemo
        </h1>
        <p style="color: #94A3B8; font-size: 1.1rem;">
            视频 AI 处理工具
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Task Management Section
    st.markdown("### 📋 任务管理")

    col_new, col_spacer = st.columns([1, 3])

    with col_new:
        if st.button("➕ 新建任务", use_container_width=True):
            task = TaskManager.create_new_task()
            st.session_state['nav_to_page'] = "1_📹_视频上传"
            st.rerun()

    st.markdown("")

    # Load existing tasks
    st.markdown("#### 📂 我的任务")

    tasks = TaskManager.list_tasks()

    if tasks:
        for task_id in tasks:
            info = TaskManager.get_task_info(task_id)
            if info:
                status_text, status_color = get_status_display(info['status'])

                # Format dates
                created = info['created_at'][:10] if info['created_at'] else 'N/A'

                # Determine if task has video
                has_video = "📹" if info.get('has_video') else "⭕"
                has_analysis = "✅" if info.get('has_keyframes') else "❌"

                with st.container():
                    cols = st.columns([5, 1, 1, 1, 2])

                    with cols[0]:
                        st.markdown(f"""
                        <div style="color: #F8FAFC; font-weight: 600;">{task_id[:8]}...</div>
                        <div style="color: {status_color}; font-size: 0.875rem;">{status_text}</div>
                        <div style="color: #94A3B8; font-size: 0.75rem; margin-top: 0.25rem;">创建于 {created}</div>
                        """, unsafe_allow_html=True)

                        if st.button(f"打开", key=f"open_{task_id}"):
                            TaskManager.load_task(task_id)
                            st.session_state['nav_to_page'] = "1_📹_视频上传"
                            st.rerun()

                    with cols[1]:
                        st.markdown(f"<div style='color: #94A3B8; font-size: 0.875rem;'>{has_video}</div>", unsafe_allow_html=True)

                    with cols[2]:
                        st.markdown(f"<div style='color: #94A3B8; font-size: 0.875rem;'>{has_analysis}</div>", unsafe_allow_html=True)

                    with cols[3]:
                        pass

                    with cols[4]:
                        if st.button("🗑️", key=f"del_{task_id}"):
                            TaskManager.delete_task(task_id)
                            st.rerun()
    else:
        st.info("暂无保存的任务，点击上方「新建任务」开始")

    st.markdown("---")

    # Quick info section
    st.markdown("""
    <div style="color: #94A3B8; text-align: center; padding: 2rem 0;">
        <p style="font-size: 0.875rem;">
            上传视频 → AI 分析 → 修改提示词 → 生成新视频
        </p>
    </div>
    """, unsafe_allow_html=True)


def main():
    """Main application entry point"""
    init_session_state()

    # Check if we need to navigate to a page
    nav_page = st.session_state.get('nav_to_page')
    if nav_page:
        st.session_state['nav_to_page'] = None
        st.switch_page(f"pages/{nav_page}.py")

    current_task = TaskManager.get_current_task()

    if not current_task:
        render_welcome_page()
    else:
        # If there's a task but no navigation, render welcome page
        render_welcome_page()


if __name__ == "__main__":
    main()
