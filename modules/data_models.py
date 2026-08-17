"""Data models for RenditionDemo tasks"""

import uuid
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
    frame_index: int = 0
    timestamp: float = 0.0
    image_path: str = ""
    prompt: str = ""
    character_description: str = ""
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CharacterKeyframe':
        if 'id' not in data:
            data['id'] = str(uuid.uuid4())
        return cls(**data)


@dataclass
class ScenePrompt:
    """Scene/shot prompt"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_time: float = 0.0
    end_time: float = 0.0
    prompt: str = ""
    scene_type: str = ""
    camera_movement: str = ""
    lighting: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScenePrompt':
        if 'id' not in data:
            data['id'] = str(uuid.uuid4())
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
