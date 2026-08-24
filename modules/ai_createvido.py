import os
import time
import base64
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
# Install SDK:  pip install 'volcengine-python-sdk[ark]'
from volcenginesdkarkruntime import Ark


def image_to_base64(image_path: str) -> str:
    """读取本地图片并转换为base64格式的data URL"""
    with open(image_path, "rb") as f:
        image_data = f.read()
    base64_data = base64.b64encode(image_data).decode("utf-8")
    
    # 根据文件扩展名确定MIME类型
    ext = os.path.splitext(image_path)[1].lower()
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    mime_type = mime_types.get(ext, "image/jpeg")
    
    return f"data:{mime_type};base64,{base64_data}"


def download_video(video_url: str, save_path: str) -> bool:
    """下载视频到本地路径"""
    import urllib.request
    import urllib.error

    try:
        # 创建目录
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        # 下载视频
        urllib.request.urlretrieve(video_url, save_path)
        print(f"Video downloaded to: {save_path}")
        return True
    except Exception as e:
        print(f"Failed to download video: {e}")
        return False


@dataclass
class VideoGenerationResult:
    """视频生成结果"""
    success: bool
    task_id: str = ""
    video_url: str = ""
    video_path: str = ""  # 本地保存路径
    error_message: str = ""


client = Ark(
    # The base URL for model invocation
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    # Get API Key：https://console.volcengine.com/ark/region:cn-beijing/apikey
    api_key=os.environ.get("ARK_API_KEY"),
)


def build_prompt_with_characters(
    character_images: List[Dict[str, str]],
    scene_prompt: str,
    ai_style: str = ""
) -> str:
    """
    组装提示词，包含角色三视图绑定信息和场景描述
    
    Args:
        character_images: 角色三视图列表，每个元素包含 name 和 image_path
                         例如: [{"name": "Alice", "image_path": "/path/to/three_view.png"}, ...]
        scene_prompt: 子视频片段的提示词
        ai_style: 视频风格描述
    
    Returns:
        组装后的完整提示词
    """
    # 第一部分：角色名称与三视图绑定
    character_parts = []
    for i, char in enumerate(character_images, 1):
        character_parts.append(f"图{i}为{char['name']}人物形象")
    character_binding = "，".join(character_parts)
    
    # 组装完整提示词
    prompt_parts = [character_binding]
    
    # 第二部分：子视频片段提示词
    if scene_prompt:
        prompt_parts.append(scene_prompt)
    
    # 第三部分：视频风格描述
    if ai_style:
        prompt_parts.append(ai_style)
    
    return "\n\n".join(prompt_parts)


def generate_video_with_three_views(
    character_images: List[Dict[str, str]],
    scene_prompt: str,
    ai_style: str = "",
    ratio: str = "9:16",
    generate_audio: bool = True,
    watermark: bool = False,
    poll_interval: int = 30,
    task_dir: str = ""
) -> VideoGenerationResult:
    """
    使用角色三视图生成视频

    Args:
        character_images: 角色三视图列表，每个元素包含 name 和 image_path
                        例如: [{"name": "Alice", "image_path": "/path/to/three_view.png"}, ...]
        scene_prompt: 子视频片段的提示词
        ai_style: 视频风格描述
        ratio: 视频比例，默认 "9:16"
        generate_audio: 是否生成音频，默认 True
        watermark: 是否添加水印，默认 False
        poll_interval: 轮询间隔（秒），默认 30
        task_dir: 任务目录路径，用于保存生成的视频

    Returns:
        VideoGenerationResult: 包含成功状态和视频信息或错误信息
    """
    try:
        # 构建提示词
        prompt = build_prompt_with_characters(character_images, scene_prompt, ai_style)
        
        # 构建 content 数组
        content = [
            {
                "type": "text",
                "text": prompt,
            }
        ]
        
        # 添加角色三视图图片
        for char in character_images:
            if char.get("image_path") and os.path.exists(char["image_path"]):
                image_base64 = image_to_base64(char["image_path"])
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": image_base64
                    },
                    "role": "reference_image",
                })
        
        # 调用 API 创建任务
        print("----- create video request -----")
        create_result = client.content_generation.tasks.create(
            model="ep-20260821140158-fzg5g",
            content=content,
            generate_audio=generate_audio,
            ratio=ratio,
            duration=-1,
            watermark=watermark,
        )
        
        task_id = create_result.id
        print(f"Task created: {task_id}")
        
        # 轮询任务状态
        print("----- polling task status -----")
        while True:
            get_result = client.content_generation.tasks.get(task_id=task_id)
            status = get_result.status
            
            if status == "succeeded":
                print("----- task succeeded -----")
                print(get_result)
                video_url = ""
                video_path = ""

                # 正确获取 video_url: get_result.content.video_url
                if hasattr(get_result, 'content') and get_result.content:
                    video_url = get_result.content.video_url or ""

                # 下载视频到本地
                if video_url and task_dir:
                    video_dir = os.path.join(task_dir, "generated_videos")
                    video_filename = f"{task_id}.mp4"
                    video_path = os.path.join(video_dir, video_filename)
                    if download_video(video_url, video_path):
                        print(f"Video saved to: {video_path}")
                    else:
                        video_path = ""

                return VideoGenerationResult(
                    success=True,
                    task_id=task_id,
                    video_url=video_url,
                    video_path=video_path
                )
            elif status == "failed":
                error_msg = getattr(get_result, 'error', str(get_result))
                print(f"----- task failed -----")
                print(f"Error: {error_msg}")
                return VideoGenerationResult(
                    success=False,
                    task_id=task_id,
                    error_message=f"视频生成失败: {error_msg}"
                )
            else:
                print(f"Current status: {status}, Retrying after {poll_interval} seconds...")
                time.sleep(poll_interval)
                
    except Exception as e:
        return VideoGenerationResult(
            success=False,
            error_message=f"视频生成异常: {str(e)}"
        )


def download_video(url: str, save_path: str) -> bool:
    """下载视频到本地"""
    import requests
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Download video failed: {e}")
        return False


if __name__ == "__main__":
    # 示例用法
    character_images = [
        {
            "name": "Alic",
            "image_path": "D:\\python\\renditionDemo\\tasks\\a6fba64b-5565-47a7-8677-151340fe8aeb\\characters\\Lila\\three_view_Lila_1787216307095.png"
        },
        {
            "name": "Lisa",
            "image_path": "D:\\python\\renditionDemo\\tasks\\a6fba64b-5565-47a7-8677-151340fe8aeb\\characters\\Martha\\three_view_Martha_1787215842220.png"
        }
    ]
    
    scene_prompt = """00:00-00:01 镜头:中景镜头 空间:庄园庭院的户外区域，背景是绿植与石墙 氛围:夜晚，冷色调灯光，氛围紧张 开场:Alic神情疑惑，右手抬起靠近耳部，左手摊开 动作:Alic皱着眉头，开口说：'What?' 结尾:Alic保持疑惑的神情与姿势

00:01-00:05 镜头:中景镜头 空间:庄园庭院的户外区域，背景是绿植与石墙 氛围:夜晚，冷色调灯光，氛围紧张 开场:Lisa双手握拐杖，神情严肃 动作:Lisa开口说：'Master.'，随后身体微倾，说：'What do you mean by that?' 结尾:Lisa身体微倾，保持严肃的神情"""
    
    ai_style = "电影风格，欧美氛围，高质量画面"
    
    result = generate_video_with_three_views(
        character_images=character_images,
        scene_prompt=scene_prompt,
        ai_style=ai_style,
        ratio="9:16"
    )
    
    if result.success:
        print(f"视频生成成功! Task ID: {result.task_id}")
        print(f"Video URL: {result.video_url}")
    else:
        print(f"视频生成失败: {result.error_message}")
