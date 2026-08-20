import os
import time
import base64
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


client = Ark(
    # The base URL for model invocation
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    # Get API Key：https://console.volcengine.com/ark/region:cn-beijing/apikey
    api_key=os.environ.get("ARK_API_KEY"),
)

if __name__ == "__main__":
    # 示例：读取本地图片并转换为base64格式
    local_image_path = "D:\\python\\renditionDemo\\tasks\\a6fba64b-5565-47a7-8677-151340fe8aeb\\characters\\Lila\\three_view_Lila_1787216307095.png"  # 替换为你的本地图片路径
    image_base64_data = image_to_base64(local_image_path)

    local_image2_path = "D:\\python\\renditionDemo\\tasks\\a6fba64b-5565-47a7-8677-151340fe8aeb\\characters\\Martha\\three_view_Martha_1787215842220.png"
    image2_base64_data = image_to_base64(local_image2_path)


    print("----- create request -----")
    create_result = client.content_generation.tasks.create(
        model="ep-20260820135741-2lkpj", # Replace with Model ID
        content=[
            {
                "type": "text",
                "text": "图1为Alic的AI形象图，图2为Lisa的AI形象图\n\n"
                        "00:00-00:01 镜头:中景镜头 空间:庄园庭院的户外区域，背景是绿植与石墙 氛围:夜晚，冷色调灯光，氛围紧张 开场:Alic神情疑惑，右手抬起靠近耳部，左手摊开 动作:Alic皱着眉头，开口说：'What?' 结尾:Alic保持疑惑的神情与姿势\n\n"
                        "00:01-00:05 镜头:中景镜头 空间:庄园庭院的户外区域，背景是绿植与石墙 氛围:夜晚，冷色调灯光，氛围紧张 开场:Lisa双手握拐杖，神情严肃 动作:Lisa开口说：'Master.'，随后身体微倾，说：'What do you mean by that?' 结尾:Lisa身体微倾，保持严肃的神情\n\n",
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": image_base64_data
                },
                "role": "reference_image",
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": image2_base64_data
                },
                "role": "reference_image",
            },
        ],
        generate_audio=True,
        ratio="9:16",
        duration=-1,
        watermark=False,
    )
    print(create_result)


    # Polling query section
    print("----- polling task status -----")
    task_id = create_result.id
    while True:
        get_result = client.content_generation.tasks.get(task_id=task_id)
        status = get_result.status
        if status == "succeeded":
            print("----- task succeeded -----")
            print(get_result)
            break
        elif status == "failed":
            print("----- task failed -----")
            print(f"Error: {get_result.error}")
            break
        else:
            print(f"Current status: {status}, Retrying after 30 seconds...")
            time.sleep(30)