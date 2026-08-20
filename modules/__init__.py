"""RenditionDemo - Video Processing with AI"""

from .data_models import (
    Task,
    SourceVideo,
    CharacterKeyframe,
    ScenePrompt,
    GeneratedVideo,
    TaskStatus,
)
from .task_manager import TaskManager
from .ai_interface import AIInterface, AnalysisResult, GenerationResult
from .config import Config
from .video_utils import (
    extract_frame_at_timestamp,
    extract_frame_from_timestamp_str,
    parse_timestamp,
    get_video_info,
    FrameExtractionResult,
)
from .ai_image import (
    generate_character_three_view,
    ImageGenerationResult,
)

__all__ = [
    'Task',
    'SourceVideo',
    'CharacterKeyframe',
    'ScenePrompt',
    'GeneratedVideo',
    'TaskStatus',
    'TaskManager',
    'AIInterface',
    'AnalysisResult',
    'GenerationResult',
    'Config',
    'extract_frame_at_timestamp',
    'extract_frame_from_timestamp_str',
    'parse_timestamp',
    'get_video_info',
    'FrameExtractionResult',
    'generate_character_three_view',
    'ImageGenerationResult',
]
