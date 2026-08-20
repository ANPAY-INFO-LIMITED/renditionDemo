"""AI interface for video processing APIs"""

import asyncio
import json
import re
import uuid
import time
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass

from .data_models import (
    Task,
    CharacterKeyframe,
    ScenePrompt,
    CharacterInShot,
    SourceVideo,
    GeneratedVideo,
    TaskStatus,
)
from .config import Config
from .video_utils import extract_frame_from_timestamp_str, FrameExtractionResult


def build_character_prompt(description: str, facial_features: str, costume: str) -> str:
    """
    Build a unified character prompt for three-view generation.
    
    Args:
        description: Character description
        facial_features: Facial features
        costume: Costume/attire
    
    Returns:
        Full prompt for three-view generation
    """
    prompt_parts = []
    if description:
        prompt_parts.append(f"角色: {description}")
    if facial_features:
        prompt_parts.append(f"面部特征: {facial_features}")
    if costume:
        prompt_parts.append(f"服饰: {costume}")
    
    base_prompt = "，".join(prompt_parts) if prompt_parts else ""
    
    return f"""参考图片中的人物形象，生成该角色的欧美风格三视图（正面、侧面、背面）。
要求：
1. 保持参考图中人物的面部特征和五官比例
2. 保持参考图中人物的服饰和造型
3. 三视图清晰展示人物的正面、侧面（左侧或右侧）、背面姿态
4. 人物站在纯色背景前，姿态自然
5. 欧美真人风格，真实感强

{base_prompt}"""


@dataclass
class AnalysisResult:
    """Result from video analysis"""
    success: bool
    message: str
    character_keyframes: List[CharacterKeyframe] = None
    scene_prompts: List[ScenePrompt] = None
    ai_style: str = ""
    ai_scene: str = ""
    raw_result: str = ""
    error: Optional[str] = None


@dataclass
class GenerationResult:
    """Result from video generation"""
    success: bool
    message: str
    video_path: Optional[str] = None
    error: Optional[str] = None


def parse_duration(duration_str: str) -> float:
    """Parse duration string like '3s', '3.5s', '00:04', '4:30' to float seconds"""
    if not duration_str:
        return 0.0
    
    duration_str = str(duration_str).strip()
    
    # Handle MM:SS or HH:MM:SS format
    if ':' in duration_str:
        parts = duration_str.split(':')
        try:
            if len(parts) == 2:
                # MM:SS format
                minutes, seconds = parts
                return int(minutes) * 60 + float(seconds)
            elif len(parts) == 3:
                # HH:MM:SS format
                hours, minutes, seconds = parts
                return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        except (ValueError, TypeError):
            pass
    
    # Handle plain number or number with 's' suffix
    match = re.search(r'(\d+(?:\.\d+)?)', duration_str)
    if match:
        return float(match.group(1))
    
    return 0.0


def fix_json_quotes(json_str: str) -> str:
    """Fix Chinese quotes and other common JSON issues"""
    # Replace Chinese quotes with English quotes
    replacements = [
        ('"', '"'), ('"', '"'),  # Left/right double quotes
        ("'", "'"), ("'", "'"),  # Left/right single quotes
        ("：", ":"),  # Full-width colon
        ("，", ","),  # Full-width comma
        ("【", '"'), ("】", '"'),  # Brackets to quotes for simple fields
        ("＝", "="),  # Full-width equals
        ("；", ";"),  # Full-width semicolon
    ]
    
    result = json_str
    for old, new in replacements:
        result = result.replace(old, new)
    
    return result


def extract_json_from_response(response: str) -> dict:
    """Extract and parse JSON from AI response with robust error handling"""
    # Clean the response
    cleaned = response.strip()
    
    # Remove markdown code blocks
    if cleaned.startswith('```json'):
        cleaned = cleaned[7:]
    elif cleaned.startswith('```'):
        cleaned = cleaned[3:]
    if cleaned.endswith('```'):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    
    # Try direct parsing first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    
    # Try fixing quotes
    try:
        fixed = fix_json_quotes(cleaned)
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass
    
    # Try finding JSON object pattern
    json_match = re.search(r'\{[\s\S]*\}', cleaned)
    if json_match:
        json_str = json_match.group()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Try with fixed quotes
            try:
                fixed = fix_json_quotes(json_str)
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass
    
    raise ValueError(f"无法解析JSON响应")


def parse_ai_json_response(json_str: str) -> Tuple[List[CharacterKeyframe], str, str, dict]:
    """
    Parse AI JSON response into structured data.
    
    Args:
        json_str: Raw JSON string from AI response
    
    Returns:
        Tuple of (character_keyframes, style, scene, parsed_data)
    """
    # Extract and parse JSON
    try:
        data = extract_json_from_response(json_str)
    except ValueError as e:
        raise ValueError(f"JSON解析失败: {e}\n原始响应: {json_str[:500]}...")
    
    # Extract style and scene
    style = data.get('style', '')
    scene = data.get('scene', '')
    
    # Parse characters
    characters = []
    for char_data in data.get('characters', []):
        character_id = char_data.get('id', 0)
        
        # Parse best_frame timestamp (e.g., "0:07" -> 7.0 seconds)
        best_frame_str = char_data.get('best_frame', '')
        timestamp = 0.0
        if best_frame_str:
            match = re.match(r'(\d+):(\d+)', str(best_frame_str))
            if match:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                timestamp = minutes * 60 + seconds
        
        character = CharacterKeyframe(
            id=str(uuid.uuid4()),
            character_id=character_id,
            name=char_data.get('name', ''),
            timestamp=timestamp,
            prompt=build_character_prompt(
                description=char_data.get('description', ''),
                facial_features=char_data.get('facial_features', ''),
                costume=char_data.get('costume', '')
            ),
            best_frame=best_frame_str,
            confidence=1.0  # AI生成的数据置信度为1.0
        )
        characters.append(character)
    
    # Sort characters by character_id
    characters.sort(key=lambda x: x.character_id)
    
    return characters, style, scene, data


def analyze_video_with_ai(video_path: str, task_id: str) -> AnalysisResult:
    """
    Analyze video using the AI interface from process_video_prompt.py
    
    Args:
        video_path: Path to the uploaded video file
        task_id: Current task ID
    
    Returns:
        AnalysisResult with extracted data or error
    """
    try:
        # Import the process_video_prompt module
        import sys
        modules_path = Path(__file__).parent.parent / 'modules'
        if str(modules_path) not in sys.path:
            sys.path.insert(0, str(modules_path))
        
        from process_video_prompt import (
            convert_txt_to_pdf,
            upload_pdf,
            upload_video,
            generate_prompt_from_video
        )
        
        # Get the json_example.txt path
        base_dir = Path(__file__).parent.parent
        json_example_path = base_dir / 'modules' / 'json_example.txt'
        
        if not json_example_path.exists():
            return AnalysisResult(
                success=False,
                message="未找到参考JSON文件",
                error=f"文件不存在: {json_example_path}"
            )
        
        # Convert txt to pdf and upload
        pdf_file = convert_txt_to_pdf(str(json_example_path))
        json_file_id = upload_pdf(pdf_file)
        video_file_id = upload_video(video_path)
        
        # Call AI with custom prompt
        prompt_text = ("请反推视频提示词,要求如下:\n\n"
                       "1.以上传文件中的json格式输出。"
                       "2.最佳角色展示帧展示对应角色正面形象，取连续展示人物片段的中间帧，采用 (HH:MM:SS:FF)格式，精确到帧."
                       "3.角色相似度大于0.7（满值为1）应当视为同一角色\n\n"
                       "4.人物指代使用姓名。\n\n"
                       "5.将一个连续的画面及对话归为一个镜头，切保证镜头时长总和与原视频一致。\n\n"
                       "6.同时将提示词内容改写为欧美真人剧风格，整体剧情结构不变，人物特征，名称，服装，场景本土化。\n\n"
                       "7.严格保证提示词整体使用中文，仅名称和对话使用英文")
        raw_response = generate_prompt_from_video(video_file_id, json_file_id, prompt_text)

        # Clean up temp PDF
        if Path(pdf_file).exists():
            Path(pdf_file).unlink()

        # Save raw result immediately (before parsing) for debugging
        task_dir = Config.get_task_dir(task_id)
        raw_result_file = task_dir / 'ai_raw_response.txt'
        with open(raw_result_file, 'w', encoding='utf-8') as f:
            f.write(raw_response)

        # Parse the result
        try:
            characters, style, scene, parsed_data = parse_ai_json_response(raw_response)
        except Exception as parse_error:
            return AnalysisResult(
                success=False,
                message="JSON解析失败",
                error=f"解析错误: {parse_error}\n\n原始响应已保存至: {raw_result_file}",
                raw_result=raw_response
            )

        # Parse scene_prompts from AI response
        scene_prompts = []
        shots_data = parsed_data.get('shots', [])
        cumulative_time = 0.0
        
        for idx, shot_data in enumerate(shots_data):
            # Parse duration from time string like "3s" or "0-3s"
            duration = parse_duration(shot_data.get('time', '0'))
            
            # Parse characters in shot
            characters_in_shot = []
            for char_data in shot_data.get('characters_in_shot', []):
                characters_in_shot.append(CharacterInShot(
                    name=char_data.get('name', ''),
                    pose=char_data.get('pose', ''),
                    position=char_data.get('position', '')
                ))
            
            # Build combined prompt from shot data
            prompt_parts = []
            if shot_data.get('opening_frame'):
                prompt_parts.append(f"开场: {shot_data['opening_frame']}")
            if shot_data.get('continuous_action'):
                prompt_parts.append(f"动作: {shot_data['continuous_action']}")
            if shot_data.get('end_state'):
                prompt_parts.append(f"结尾: {shot_data['end_state']}")
            
            scene_prompt = ScenePrompt(
                id=str(uuid.uuid4()),
                start_time=cumulative_time,
                end_time=cumulative_time + duration,
                continuous_action=shot_data.get('continuous_action', ''),
                space=shot_data.get('space', ''),
                time_atmosphere=shot_data.get('time_atmosphere', ''),
                camera=shot_data.get('camera', ''),
                characters_in_shot=characters_in_shot,
                transition=shot_data.get('transition', ''),
                opening_frame=shot_data.get('opening_frame', ''),
                end_state=shot_data.get('end_state', ''),
                # Legacy fields
                prompt="; ".join(prompt_parts) if prompt_parts else shot_data.get('opening_frame', ''),
                scene_type=shot_data.get('camera', '')
            )
            scene_prompts.append(scene_prompt)
            cumulative_time += duration
        
        # Extract best frame images for each character
        for char in characters:
            if char.best_frame:
                char_dir = task_dir / 'characters' / char.name
                frame_result = extract_frame_from_timestamp_str(
                    video_path=video_path,
                    timestamp_str=char.best_frame,
                    output_dir=str(char_dir),
                    filename_prefix=f"best_frame_{char.name}"
                )
                if frame_result.success:
                    char.best_frame_image_path = frame_result.image_path

        # Save parsed result to task directory
        result_file = task_dir / 'ai_analysis_result.json'
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                'raw_result': raw_response[:1000] + '...' if len(raw_response) > 1000 else raw_response,
                'parsed': {
                    'style': style,
                    'scene': scene,
                    'characters_count': len(characters),
                    'shots_count': len(scene_prompts)
                }
            }, f, ensure_ascii=False, indent=2)
        
        return AnalysisResult(
            success=True,
            message=f"分析完成：{len(characters)}个角色，{len(scene_prompts)}个镜头",
            character_keyframes=characters,
            scene_prompts=scene_prompts,
            ai_style=style,
            ai_scene=scene,
            raw_result=raw_response
        )
        
    except Exception as e:
        return AnalysisResult(
            success=False,
            message="视频分析失败",
            error=str(e)
        )


class AIInterface:
    """AI interface for video analysis and generation"""

    @staticmethod
    def analyze_video(video_path: str, task_id: str) -> AnalysisResult:
        """
        Analyze video to extract character keyframes and scene prompts.
        
        This method calls the actual AI interface from process_video_prompt.py.
        
        Args:
            video_path: Path to the uploaded video file
            task_id: Current task ID for saving extracted frames
        
        Returns:
            AnalysisResult with extracted data or error
        """
        return analyze_video_with_ai(video_path, task_id)

    @staticmethod
    def extract_character_prompts(
        video_path: str,
        keyframes: List[Tuple[int, float, str]]
    ) -> List[CharacterKeyframe]:
        """
        Extract character prompts from keyframes.

        This is a placeholder implementation.

        Args:
            video_path: Path to the video
            keyframes: List of (frame_index, timestamp, image_path) tuples

        Returns:
            List of CharacterKeyframe objects
        """
        # TODO: Implement actual character prompt extraction
        # This should use a vision model to:
        # 1. Identify characters in each keyframe
        # 2. Generate detailed character descriptions
        # 3. Return structured prompts

        character_keyframes = []

        for idx, (frame_idx, timestamp, _) in enumerate(keyframes):
            keyframe = CharacterKeyframe(
                id=str(uuid.uuid4()),
                frame_index=frame_idx,
                timestamp=timestamp,
                prompt=f"Character {idx + 1}: A person with distinctive appearance",
                character_description=f"Person in frame {frame_idx}",
                confidence=0.85
            )
            character_keyframes.append(keyframe)

        return character_keyframes

    @staticmethod
    def extract_scene_prompts(
        video_path: str,
        shots: List[Tuple[float, float]]
    ) -> List[ScenePrompt]:
        """
        Extract scene/shots prompts from video.

        This is a placeholder implementation.

        Args:
            video_path: Path to the video
            shots: List of (start_time, end_time) tuples

        Returns:
            List of ScenePrompt objects
        """
        # TODO: Implement actual scene prompt extraction
        # This should use video analysis to:
        # 1. Analyze visual content of each shot
        # 2. Generate descriptive prompts
        # 3. Identify camera movements
        # 4. Describe lighting conditions

        scene_prompts = []

        for idx, (start_time, end_time) in enumerate(shots):
            prompt = ScenePrompt(
                id=str(uuid.uuid4()),
                start_time=start_time,
                end_time=end_time,
                prompt=f"Scene {idx + 1}: Dynamic shot with natural lighting",
                scene_type="general",
                camera="static",
                time_atmosphere="natural"
            )
            scene_prompts.append(prompt)

        return scene_prompts

    @staticmethod
    def generate_video(
        task: Task,
        output_path: str,
        progress_callback=None
    ) -> GenerationResult:
        """
        Generate new video from character and scene prompts.

        This is a placeholder implementation.

        Args:
            task: The task containing modified prompts
            output_path: Where to save the generated video
            progress_callback: Optional callback for progress updates

        Returns:
            GenerationResult with output path or error
        """
        # TODO: Implement actual video generation
        # This should:
        # 1. Combine character prompts from page 2
        # 2. Combine scene prompts from page 3
        # 3. Call video generation API
        # 4. Return path to generated video

        print(f"[AIInterface] Generating video for task: {task.task_id}")

        if progress_callback:
            progress_callback(0.1)
            time.sleep(0.5)
            progress_callback(0.5)
            time.sleep(0.5)
            progress_callback(1.0)

        # Placeholder: No video generated
        return GenerationResult(
            success=True,
            message="Video generation complete (placeholder)",
            video_path=None
        )

    @staticmethod
    def extract_keyframes_from_video(
        video_path: str,
        task_id: str,
        max_frames: int = 10,
        interval: float = 5.0
    ) -> List[Tuple[int, float, str]]:
        """
        Extract key frames from video for analysis.

        This is a placeholder using basic frame extraction.
        In production, use more sophisticated keyframe detection.

        Args:
            video_path: Path to video file
            task_id: Task ID for saving frames
            max_frames: Maximum number of frames to extract
            interval: Interval between frames in seconds

        Returns:
            List of (frame_index, timestamp, image_path) tuples
        """
        # TODO: Implement actual keyframe extraction
        # Consider using:
        # - OpenCV for basic frame extraction
        # - Content-based keyframe detection
        # - Scene detection algorithms

        print(f"[AIInterface] Extracting keyframes from: {video_path}")

        # Placeholder: Return empty list
        # In real implementation:
        # 1. Open video with cv2
        # 2. Extract frames at regular intervals
        # 3. Save frames to keyframes directory
        # 4. Return list of saved frame paths

        return []

    @staticmethod
    def get_video_info(video_path: str) -> Optional[SourceVideo]:
        """
        Get video metadata.

        This is a placeholder implementation.

        Args:
            video_path: Path to video file

        Returns:
            SourceVideo object or None
        """
        # TODO: Implement actual video info extraction using cv2

        video_path_obj = Path(video_path)
        if not video_path_obj.exists():
            return None

        return SourceVideo(
            path=str(video_path),
            duration=0.0,  # Will be extracted by cv2
            width=0,
            height=0,
            fps=0.0,
            file_size=video_path_obj.stat().st_size
        )
