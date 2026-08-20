"""AI图像生成模块"""

import base64
import os
import time
import requests
from typing import Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

try:
    from volcenginesdkarkruntime import Ark
    ARK_AVAILABLE = True
except ImportError:
    ARK_AVAILABLE = False


def image_to_base64(image_path: str) -> str:
    """Convert local image to Base64 encoding in data URL format."""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded_string}"


def download_image(url: str, save_path: str) -> str:
    """Download image from URL and save to specified path."""
    response = requests.get(url)
    response.raise_for_status()
    
    with open(save_path, "wb") as f:
        f.write(response.content)
    return save_path


@dataclass
class ImageGenerationResult:
    """图像生成结果"""
    success: bool
    image_path: str = ""
    error_message: str = ""


def generate_character_three_view(
    prompt: str,
    output_dir: str,
    character_name: str = "character"
) -> ImageGenerationResult:
    """
    根据提示词生成角色三视图（不再使用参考图片）
    
    Args:
        prompt: 提示词
        output_dir: 输出目录
        character_name: 角色名称，用于生成文件名
    
    Returns:
        ImageGenerationResult: 包含成功状态和图片路径或错误信息
    """
    if not ARK_AVAILABLE:
        return ImageGenerationResult(
            success=False,
            error_message="未安装 volcengine-python-sdk，请运行: pip install 'volcengine-python-sdk[ark]'"
        )
    
    try:
        client = Ark(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=os.getenv('ARK_API_KEY'),
        )
        
        # 生成图片（仅使用提示词，不传入参考图）
        images_response = client.images.generate(
            model="ep-20260820164114-mjmhf",
            prompt=prompt,
            size="2K",
            output_format="png",
            response_format="url",
            watermark=False
        )
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名（使用时间戳避免重复）
        timestamp = int(time.time() * 1000)
        output_filename = f"three_view_{character_name}_{timestamp}.png"
        output_path = os.path.join(output_dir, output_filename)
        
        # 下载并保存图片
        download_image(images_response.data[0].url, output_path)

        print(images_response.usage)
        
        return ImageGenerationResult(
            success=True,
            image_path=output_path
        )
        
    except Exception as e:
        return ImageGenerationResult(
            success=False,
            error_message=f"生成三视图失败: {str(e)}"
        )


if __name__ == "__main__":
    # 测试代码（不再需要本地图片）
    test_output = "D:\\python\\renditionDemo\\tasks\\a06dd52f-9071-4bda-942a-50349ec65e3f\\characters\\Eleanor"
    
    result = generate_character_three_view(
        prompt="生成欧美风格三视图（正面、侧面、背面），展现人物面部特征和服饰细节",
        output_dir=test_output,
        character_name="Eleanor"
    )
    
    if result.success:
        print(f"三视图已生成: {result.image_path}")
    else:
        print(f"生成失败: {result.error_message}")
