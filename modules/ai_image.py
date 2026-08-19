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
    reference_image_path: str,
    prompt: str,
    output_dir: str,
    character_name: str = "character"
) -> ImageGenerationResult:
    """
    根据参考图和提示词生成角色三视图
    
    Args:
        reference_image_path: 参考图片路径（最佳展示帧）
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
        
        # 检查参考图片是否存在
        if not os.path.exists(reference_image_path):
            return ImageGenerationResult(
                success=False,
                error_message=f"参考图片不存在: {reference_image_path}"
            )
        
        # 转换参考图片为 base64
        image_base64 = image_to_base64(reference_image_path)
        
        # 生成图片
        images_response = client.images.generate(
            model="ep-20260819135919-p9rxq",
            prompt=prompt,
            image=image_base64,
            size="1K",
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
        
        return ImageGenerationResult(
            success=True,
            image_path=output_path
        )
        
    except Exception as e:
        return ImageGenerationResult(
            success=False,
            error_message=f"生成三视图失败: {str(e)}"
        )


def build_three_view_prompt(character_name: str, character_description: str, 
                            facial_features: str, costume: str) -> str:
    """
    构建三视图生成的提示词
    
    Args:
        character_name: 角色名称
        character_description: 角色描述
        facial_features: 面部特征
        costume: 服饰描述
    
    Returns:
        组合后的提示词
    """
    prompt_parts = []
    
    if character_description:
        prompt_parts.append(f"角色: {character_description}")
    if facial_features:
        prompt_parts.append(f"面部特征: {facial_features}")
    if costume:
        prompt_parts.append(f"服饰: {costume}")
    
    base_prompt = "，".join(prompt_parts) if prompt_parts else ""
    
    full_prompt = f"""参考图片中的人物形象，生成该角色的欧美风格三视图（正面、侧面、背面）。
要求：
1. 保持参考图中人物的面部特征和五官比例
2. 保持参考图中人物的服饰和造型
3. 三视图清晰展示人物的正面、侧面（左侧或右侧）、背面姿态
4. 人物站在纯色背景前，姿态自然
5. 欧美真人风格，真实感强

{base_prompt}"""
    
    return full_prompt


if __name__ == "__main__":
    # 测试代码
    test_image = "D:\\python\\renditionDemo\\tasks\\a06dd52f-9071-4bda-942a-50349ec65e3f\\characters\\Eleanor\\best_frame_Eleanor_3.00s.jpg"
    test_output = "D:\\python\\renditionDemo\\tasks\\a06dd52f-9071-4bda-942a-50349ec65e3f\\characters\\Eleanor"
    
    result = generate_character_three_view(
        reference_image_path=test_image,
        prompt="参考图片中人物形象，生成欧美风格三视图（正面、侧面、背面），保持人物面部特征和服饰",
        output_dir=test_output,
        character_name="Eleanor"
    )
    
    if result.success:
        print(f"三视图已生成: {result.image_path}")
    else:
        print(f"生成失败: {result.error_message}")
