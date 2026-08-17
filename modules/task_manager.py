"""Task manager for handling task persistence and loading"""

import json
import shutil
from pathlib import Path
from typing import Optional, List
import streamlit as st

from .data_models import Task, TaskStatus
from .config import Config


class TaskManager:
    """Manages task persistence and loading"""

    _current_task: Optional[Task] = None
    _tasks_cache: Optional[List[str]] = None

    @classmethod
    def get_current_task(cls) -> Optional[Task]:
        """Get the current active task"""
        if hasattr(st, 'session_state') and 'current_task' in st.session_state:
            return st.session_state['current_task']
        return cls._current_task

    @classmethod
    def set_current_task(cls, task: Optional[Task]) -> None:
        """Set the current active task"""
        if hasattr(st, 'session_state'):
            st.session_state['current_task'] = task
        cls._current_task = task
        cls._tasks_cache = None  # Invalidate cache

    @classmethod
    def create_new_task(cls) -> Task:
        """Create a new task"""
        task = Task()
        Config.ensure_tasks_dir()
        cls._save_task_to_disk(task)
        cls.set_current_task(task)
        return task

    @classmethod
    def _get_task_file_path(cls, task_id: str) -> Path:
        """Get the path to a task's JSON file"""
        return Config.get_task_dir(task_id) / "task.json"

    @classmethod
    def _save_task_to_disk(cls, task: Task) -> None:
        """Save task to disk"""
        task_file = cls._get_task_file_path(task.task_id)
        task.updated_at = task.to_dict()['updated_at']

        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(task.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def save_task(cls, task: Task) -> None:
        """Save task to disk and update session state"""
        cls._save_task_to_disk(task)
        if cls.get_current_task() and cls.get_current_task().task_id == task.task_id:
            cls.set_current_task(task)

    @classmethod
    def load_task(cls, task_id: str) -> Optional[Task]:
        """Load a task from disk"""
        task_file = cls._get_task_file_path(task_id)

        if not task_file.exists():
            return None

        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            task = Task.from_dict(data)
            cls.set_current_task(task)
            return task
        except Exception as e:
            print(f"Error loading task {task_id}: {e}")
            return None

    @classmethod
    def list_tasks(cls, force_refresh: bool = False) -> List[str]:
        """List all saved task IDs"""
        if cls._tasks_cache and not force_refresh:
            return cls._tasks_cache

        Config.ensure_tasks_dir()
        task_ids = []

        for task_dir in Config.TASKS_DIR.iterdir():
            if task_dir.is_dir():
                task_file = task_dir / "task.json"
                if task_file.exists():
                    task_ids.append(task_dir.name)

        # Sort by modification time (newest first)
        task_ids.sort(
            key=lambda tid: Config.get_task_dir(tid).stat().st_mtime,
            reverse=True
        )

        cls._tasks_cache = task_ids
        return task_ids

    @classmethod
    def delete_task(cls, task_id: str) -> bool:
        """Delete a task and all its files"""
        try:
            task_dir = Config.get_task_dir(task_id)
            if task_dir.exists():
                shutil.rmtree(task_dir)

            # Clear current task if it was deleted
            current = cls.get_current_task()
            if current and current.task_id == task_id:
                cls.set_current_task(None)

            cls._tasks_cache = None  # Invalidate cache
            return True
        except Exception as e:
            print(f"Error deleting task {task_id}: {e}")
            return False

    @classmethod
    def get_task_info(cls, task_id: str) -> Optional[dict]:
        """Get basic info about a task without loading full data"""
        task_file = cls._get_task_file_path(task_id)

        if not task_file.exists():
            return None

        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return {
                'task_id': data.get('task_id'),
                'created_at': data.get('created_at'),
                'updated_at': data.get('updated_at'),
                'status': data.get('status'),
                'has_video': 'source_video' in data and data['source_video'] is not None,
                'has_keyframes': 'character_keyframes' in data and len(data.get('character_keyframes', [])) > 0,
                'has_scenes': 'scene_prompts' in data and len(data.get('scene_prompts', [])) > 0,
                'has_generated': 'generated_video' in data and data['generated_video'] is not None,
            }
        except Exception as e:
            print(f"Error getting task info {task_id}: {e}")
            return None

    @classmethod
    def get_relative_path(cls, task_id: str, absolute_path: str) -> str:
        """Convert absolute path to relative path for storage"""
        task_dir = Config.get_task_dir(task_id)
        abs_path = Path(absolute_path)

        try:
            return str(abs_path.relative_to(task_dir))
        except ValueError:
            return str(abs_path)

    @classmethod
    def get_absolute_path(cls, task_id: str, relative_path: str) -> Path:
        """Convert relative path to absolute path"""
        return Config.get_task_dir(task_id) / relative_path
