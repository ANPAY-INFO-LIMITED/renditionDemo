"""视频拼接模块 - 使用 MoviePy"""

import os
from pathlib import Path
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class VideoConcatResult:
    """视频拼接结果"""
    success: bool
    output_path: str = ""
    error_message: str = ""
    duration: float = 0.0


def concat_videos(video_paths: List[str], output_path: str, progress_callback=None) -> VideoConcatResult:
    """
    使用 MoviePy 拼接多个视频

    Args:
        video_paths: 视频文件路径列表
        output_path: 输出文件路径
        progress_callback: 进度回调函数 (current, total)

    Returns:
        VideoConcatResult: 拼接结果
    """
    if not video_paths:
        return VideoConcatResult(success=False, error_message="没有可拼接的视频")

    # 检查文件是否存在
    for path in video_paths:
        if not os.path.exists(path):
            return VideoConcatResult(success=False, error_message=f"视频文件不存在: {path}")

    try:
        from moviepy.editor import VideoFileClip, concatenate_videoclips
    except ImportError:
        try:
            from moviepy import VideoFileClip, concatenate_videoclips
        except ImportError as e:
            return VideoConcatResult(
                success=False,
                error_message=f"请先安装 moviepy: pip install moviepy\n错误详情: {e}"
            )

    try:
        clips = []
        total = len(video_paths)

        # 加载所有视频片段
        for i, path in enumerate(video_paths):
            clip = VideoFileClip(path)
            clips.append(clip)

            if progress_callback:
                progress_callback(i + 1, total)

        # 拼接视频
        final_clip = concatenate_videoclips(clips, method="compose")

        # 计算总时长
        total_duration = final_clip.duration

        # 写入文件
        final_clip.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            fps=30,
        )

        # 释放资源
        for clip in clips:
            clip.close()
        final_clip.close()

        return VideoConcatResult(
            success=True,
            output_path=output_path,
            duration=total_duration
        )

    except Exception as e:
        return VideoConcatResult(
            success=False,
            error_message=f"视频拼接失败: {str(e)}"
        )
