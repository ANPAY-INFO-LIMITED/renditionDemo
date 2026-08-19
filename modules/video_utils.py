"""视频处理工具模块"""

import os
import cv2
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class FrameExtractionResult:
    """帧提取结果"""
    success: bool
    image_path: str = ""
    error_message: str = ""


def parse_timestamp(timestamp_str: str, video_duration: float) -> float:
    """
    解析时间戳字符串，返回秒数
    
    支持格式:
    - "1:30" -> 90秒
    - "0:07" -> 7秒
    - "1:30.5" -> 90.5秒
    - "90" -> 90秒
    - "90s" -> 90秒
    - "90.5s" -> 90.5秒
    
    Args:
        timestamp_str: 时间戳字符串
        video_duration: 视频总时长（秒），用于处理超过视频长度的时间
    
    Returns:
        时间戳对应的秒数
    """
    if not timestamp_str:
        return 0.0
    
    timestamp_str = str(timestamp_str).strip()
    
    try:
        # 纯数字格式 (90, 90.5)
        if timestamp_str.replace('.', '').isdigit():
            seconds = float(timestamp_str.replace('s', ''))
            return min(seconds, video_duration)
        
        # MM:SS 或 MM:SS.ss 格式
        if ':' in timestamp_str:
            parts = timestamp_str.split(':')
            if len(parts) == 2:
                minutes, seconds = parts
                total_seconds = int(minutes) * 60 + float(seconds)
                return min(total_seconds, video_duration)
        
        # 尝试直接转为浮点数
        total_seconds = float(timestamp_str.replace('s', ''))
        return min(total_seconds, video_duration)
    except (ValueError, TypeError):
        return 0.0


def extract_frame_at_timestamp(
    video_path: str,
    timestamp: float,
    output_dir: str,
    filename_prefix: str = "frame",
    quality: int = 95
) -> FrameExtractionResult:
    """
    提取视频指定时间戳的帧作为图片
    
    Args:
        video_path: 视频文件路径
        timestamp: 时间戳（秒）
        output_dir: 输出目录
        filename_prefix: 输出文件名前缀
        quality: JPEG质量 (0-100)
    
    Returns:
        FrameExtractionResult: 包含成功状态、图片路径或错误信息
    """
    try:
        # 验证视频文件存在
        if not os.path.exists(video_path):
            return FrameExtractionResult(
                success=False,
                error_message=f"视频文件不存在: {video_path}"
            )
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 打开视频
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return FrameExtractionResult(
                success=False,
                error_message=f"无法打开视频: {video_path}"
            )
        
        try:
            # 获取视频信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            if duration <= 0:
                return FrameExtractionResult(
                    success=False,
                    error_message="视频时长为0或无法获取"
                )
            
            # 确保时间戳有效
            timestamp = max(0.0, min(timestamp, duration - 0.01))
            
            # 计算目标帧位置
            target_frame = int(timestamp * fps)
            
            # 跳转到目标帧
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            
            # 读取帧
            ret, frame = cap.read()
            if not ret or frame is None:
                return FrameExtractionResult(
                    success=False,
                    error_message=f"无法读取帧 at {timestamp:.2f}s"
                )
            
            # 生成输出文件路径
            output_filename = f"{filename_prefix}_{timestamp:.2f}s.jpg"
            output_path = os.path.join(output_dir, output_filename)
            
            # 保存图片
            success = cv2.imwrite(
                output_path, 
                frame, 
                [cv2.IMWRITE_JPEG_QUALITY, quality]
            )
            
            if not success:
                return FrameExtractionResult(
                    success=False,
                    error_message="保存图片失败"
                )
            
            return FrameExtractionResult(
                success=True,
                image_path=output_path
            )
        
        finally:
            cap.release()
    
    except Exception as e:
        return FrameExtractionResult(
            success=False,
            error_message=f"提取帧时出错: {str(e)}"
        )


def extract_frame_from_timestamp_str(
    video_path: str,
    timestamp_str: str,
    output_dir: str,
    filename_prefix: str = "frame",
    quality: int = 95
) -> FrameExtractionResult:
    """
    从时间戳字符串提取帧
    
    Args:
        video_path: 视频文件路径
        timestamp_str: 时间戳字符串 (如 "0:07", "1:30")
        output_dir: 输出目录
        filename_prefix: 输出文件名前缀
        quality: JPEG质量 (0-100)
    
    Returns:
        FrameExtractionResult: 包含成功状态、图片路径或错误信息
    """
    # 先获取视频时长
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return FrameExtractionResult(
            success=False,
            error_message=f"无法打开视频: {video_path}"
        )
    
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
    finally:
        cap.release()
    
    # 解析时间戳
    timestamp = parse_timestamp(timestamp_str, duration)
    
    return extract_frame_at_timestamp(
        video_path=video_path,
        timestamp=timestamp,
        output_dir=output_dir,
        filename_prefix=filename_prefix,
        quality=quality
    )


def get_video_info(video_path: str) -> Optional[dict]:
    """
    获取视频信息
    
    Args:
        video_path: 视频文件路径
    
    Returns:
        包含 fps, 总帧数, 时长, 宽度, 高度的字典，失败返回 None
    """
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = total_frames / fps if fps > 0 else 0
            
            return {
                'fps': fps,
                'total_frames': total_frames,
                'duration': duration,
                'width': width,
                'height': height
            }
        finally:
            cap.release()
    except Exception:
        return None
