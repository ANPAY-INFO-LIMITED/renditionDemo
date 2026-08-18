"""Data models for RenditionDemo tasks"""

import uuid
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
import json


class TaskStatus(Enum):
    """Task status enumeration"""
    CREATED = "created"
    VIDEO_UPLOADED = "video_uploaded"
    ANALYZING = "analyzing"
    ANALYSIS_COMPLETE = "analysis_complete"
    PROMPTS_MODIFIED = "prompts_modified"
    GENERATING = "generating"
    GENERATION_COMPLETE = "generation_complete"
    ERROR = "error"


@dataclass
class SourceVideo:
    """Source video information"""
    path: str
    duration: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    file_size: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SourceVideo':
        return cls(**data)


@dataclass
class CharacterKeyframe:
    """Character keyframe with extracted prompt"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    character_id: int = 0  # AI返回的角色ID
    name: str = ""  # 角色名称
    frame_index: int = 0
    timestamp: float = 0.0
    image_path: str = ""
    prompt: str = ""
    character_description: str = ""
    facial_features: str = ""  # 面部特征
    costume: str = ""  # 服饰
    best_frame: str = ""  # 最佳展示帧位置
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CharacterKeyframe':
        if not data or not isinstance(data, dict):
            return cls()
        if 'id' not in data:
            data['id'] = str(uuid.uuid4())
        # Ensure all expected fields exist
        safe_data = {
            'id': data.get('id', str(uuid.uuid4())),
            'character_id': data.get('id', 0),  # AI返回的id作为character_id
            'name': data.get('name', ''),
            'frame_index': data.get('frame_index', 0),
            'timestamp': data.get('timestamp', 0.0),
            'image_path': data.get('image_path', ''),
            'prompt': data.get('prompt', data.get('description', '')),
            'character_description': data.get('character_description', data.get('description', '')),
            'facial_features': data.get('facial_features', ''),
            'costume': data.get('costume', ''),
            'best_frame': data.get('best_frame', ''),
            'confidence': data.get('confidence', 0.0)
        }
        return cls(**safe_data)


@dataclass
class CharacterInShot:
    """Character appearing in a shot"""
    name: str = ""
    pose: str = ""
    position: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CharacterInShot':
        return cls(**data)


@dataclass
class ScenePrompt:
    """Scene/shot prompt - matches json_example.txt shots structure"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_time: float = 0.0
    end_time: float = 0.0
    # Basic info
    continuous_action: str = ""  # 连续表演描述及人物对话
    # Shot details
    space: str = ""  # 空间/场景
    time_atmosphere: str = ""  # 时间氛围/光影 (原 lighting)
    camera: str = ""  # 镜头类型 (原 camera_movement)
    characters_in_shot: List[CharacterInShot] = field(default_factory=list)
    transition: str = ""  # 本镜开头承接动作
    opening_frame: str = ""  # 开场画面描述
    end_state: str = ""  # 镜尾状态描述

    # Legacy fields for compatibility
    prompt: str = ""  # 保留作为 combined prompt
    scene_type: str = ""  # 兼容旧代码

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        # Backward compatibility: include legacy field names
        result['lighting'] = self.time_atmosphere
        result['camera_movement'] = self.camera
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScenePrompt':
        if 'id' not in data:
            data['id'] = str(uuid.uuid4())
        # Convert characters_in_shot dicts to CharacterInShot objects
        if 'characters_in_shot' in data and isinstance(data['characters_in_shot'], list):
            data['characters_in_shot'] = [
                CharacterInShot.from_dict(c) if isinstance(c, dict) else c 
                for c in data['characters_in_shot']
            ]
        # Backward compatibility: map old field names to new ones
        if 'lighting' in data and 'time_atmosphere' not in data:
            data['time_atmosphere'] = data['lighting']
        if 'camera_movement' in data and 'camera' not in data:
            data['camera'] = data['camera_movement']
        return cls(**data)


@dataclass
class GeneratedVideo:
    """Generated video information"""
    path: str = ""
    used_character_prompts: List[str] = field(default_factory=list)
    used_scene_prompts: List[str] = field(default_factory=list)
    generated_at: Optional[str] = None
    duration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GeneratedVideo':
        return cls(**data)


@dataclass
class Task:
    """Main task data structure"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = field(default_factory=lambda: TaskStatus.CREATED.value)
    source_video: Optional[SourceVideo] = None
    character_keyframes: List[CharacterKeyframe] = field(default_factory=list)
    scene_prompts: List[ScenePrompt] = field(default_factory=list)
    generated_video: Optional[GeneratedVideo] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # AI分析结果原始数据
    ai_analysis_result: Optional[str] = None  # AI返回的原始JSON
    ai_style: str = ""  # 画面风格
    ai_scene: str = ""  # 场景名称
    shot_segments: List[Dict[str, Any]] = field(default_factory=list)  # 拆分后的镜头片段

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        data = {
            'task_id': self.task_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'status': self.status,
            'error_message': self.error_message,
            'metadata': self.metadata
        }

        if self.source_video:
            data['source_video'] = self.source_video.to_dict()

        data['character_keyframes'] = [kf.to_dict() for kf in self.character_keyframes]
        data['scene_prompts'] = [sp.to_dict() for sp in self.scene_prompts]

        if self.generated_video:
            data['generated_video'] = self.generated_video.to_dict()

        # AI分析结果
        if self.ai_analysis_result:
            data['ai_analysis_result'] = self.ai_analysis_result
        if self.ai_style:
            data['ai_style'] = self.ai_style
        if self.ai_scene:
            data['ai_scene'] = self.ai_scene
        data['shot_segments'] = self.shot_segments

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create task from dictionary"""
        task = cls()
        task.task_id = data.get('task_id', str(uuid.uuid4()))
        task.created_at = data.get('created_at', datetime.now().isoformat())
        task.updated_at = data.get('updated_at', datetime.now().isoformat())
        task.status = data.get('status', TaskStatus.CREATED.value)
        task.error_message = data.get('error_message')
        task.metadata = data.get('metadata', {})

        if 'source_video' in data and data['source_video']:
            task.source_video = SourceVideo.from_dict(data['source_video'])

        task.character_keyframes = [
            CharacterKeyframe.from_dict(kf) for kf in data.get('character_keyframes', [])
        ]

        task.scene_prompts = [
            ScenePrompt.from_dict(sp) for sp in data.get('scene_prompts', [])
        ]

        if 'generated_video' in data and data['generated_video']:
            task.generated_video = GeneratedVideo.from_dict(data['generated_video'])

        # AI分析结果
        task.ai_analysis_result = data.get('ai_analysis_result')
        task.ai_style = data.get('ai_style', '')
        task.ai_scene = data.get('ai_scene', '')
        task.shot_segments = data.get('shot_segments', [])

        return task

    def to_json(self) -> str:
        """Convert task to JSON string"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> 'Task':
        """Create task from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def update_status(self, status: TaskStatus) -> None:
        """Update task status"""
        self.status = status.value
        self.updated_at = datetime.now().isoformat()

    def update_keyframe_prompt(self, keyframe_id: str, new_prompt: str) -> None:
        """Update a keyframe prompt"""
        for kf in self.character_keyframes:
            if kf.id == keyframe_id:
                kf.prompt = new_prompt
                self.updated_at = datetime.now().isoformat()
                break

    def update_scene_prompt(self, scene_id: str, new_prompt: str) -> None:
        """Update a scene prompt"""
        for sp in self.scene_prompts:
            if sp.id == scene_id:
                sp.prompt = new_prompt
                self.updated_at = datetime.now().isoformat()
                break
