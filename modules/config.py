"""Configuration settings for RenditionDemo"""

import os
from pathlib import Path

class Config:
    """Application configuration"""

    # Base directories
    BASE_DIR = Path(__file__).parent.parent
    TASKS_DIR = BASE_DIR / "tasks"

    # Supported video formats
    VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv', '.webm']

    # Supported image formats for keyframes
    IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp']

    # Streamlit page config
    PAGE_ICON = "🎬"
    LAYOUT = "wide"

    # Theme colors (custom CSS)
    COLORS = {
        'primary': '#6366F1',
        'secondary': '#8B5CF6',
        'background': '#0F172A',
        'surface': '#1E293B',
        'text_primary': '#F8FAFC',
        'text_secondary': '#94A3B8',
        'success': '#22C55E',
        'warning': '#F59E0B',
        'error': '#EF4444',
        'border': '#334155'
    }

    # Keyframe extraction settings
    MAX_KEYFRAMES = 10
    KEYFRAME_INTERVAL = 5  # seconds

    # AI API settings (placeholders)
    AI_API_ENDPOINT = "https://api.example.com/analyze"
    AI_API_KEY = os.getenv("AI_API_KEY", "")

    # File size limits (bytes)
    MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500MB

    @classmethod
    def get_task_dir(cls, task_id: str) -> Path:
        """Get task directory path"""
        task_dir = cls.TASKS_DIR / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        return task_dir

    @classmethod
    def get_source_dir(cls, task_id: str) -> Path:
        """Get source video directory"""
        source_dir = cls.get_task_dir(task_id) / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        return source_dir

    @classmethod
    def get_keyframes_dir(cls, task_id: str) -> Path:
        """Get keyframes directory"""
        kf_dir = cls.get_task_dir(task_id) / "keyframes"
        kf_dir.mkdir(parents=True, exist_ok=True)
        return kf_dir

    @classmethod
    def get_output_dir(cls, task_id: str) -> Path:
        """Get output directory"""
        output_dir = cls.get_task_dir(task_id) / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    @classmethod
    def ensure_tasks_dir(cls) -> None:
        """Ensure tasks directory exists"""
        cls.TASKS_DIR.mkdir(parents=True, exist_ok=True)
