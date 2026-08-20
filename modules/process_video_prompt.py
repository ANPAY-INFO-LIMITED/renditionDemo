import asyncio
import os
# Install SDK:  pip install 'volcengine-python-sdk[ark]'
from volcenginesdkarkruntime import Ark
# Install PDF library: pip install reportlab
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

client = Ark(
    # 此为默认路径，您可根据业务所在地域进行配置
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    # 从环境变量中获取您的 API Key。此为默认方式，您可根据需要进行修改
    api_key=os.environ.get("ARK_API_KEY"),
)


def convert_txt_to_pdf(txt_path: str, pdf_path: str = None) -> str:
    """
    将txt文件转换为PDF

    Args:
        txt_path: txt文件路径
        pdf_path: 输出的pdf路径，默认使用同名pdf

    Returns:
        生成的PDF文件路径
    """
    if pdf_path is None:
        pdf_path = txt_path.rsplit(".", 1)[0] + ".pdf"

    with open(txt_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 注册中文字体
    font_paths = [
        ("SimHei", "C:/Windows/Fonts/simhei.ttf"),
        ("Microsoft YaHei", "C:/Windows/Fonts/msyh.ttc"),
        ("SimSun", "C:/Windows/Fonts/simsun.ttc"),
    ]

    font_name = None
    for name, path in font_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                font_name = name
                break
            except Exception:
                continue

    if font_name is None:
        raise FileNotFoundError("未找到中文字体，请检查系统字体目录")

    # 创建PDF
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    # 页面边距和行高
    left_margin = 50
    right_margin = width - 50
    top_margin = height - 50
    line_height = 14
    font_size = 11

    c.setFont(font_name, font_size)

    # 按行处理
    lines = content.split("\n")
    y_position = top_margin

    for line in lines:
        line = line.strip()
        if not line:
            # 空行
            y_position -= line_height * 0.5
            continue

        # 计算每行能容纳的字符数（粗略估算）
        max_chars_per_line = int((right_margin - left_margin) / (font_size * 0.5))

        # 如果行太长，进行自动换行
        while len(line) > max_chars_per_line:
            # 找到一个合适的断点
            break_point = max_chars_per_line
            for i in range(max_chars_per_line - 1, max(0, max_chars_per_line - 30), -1):
                if '\u4e00' <= line[i] <= '\u9fff':
                    continue
                break_point = i + 1
                break

            c.drawString(left_margin, y_position, line[:break_point])
            line = line[break_point:]
            y_position -= line_height

            if y_position < 50:
                c.showPage()
                c.setFont(font_name, font_size)
                y_position = top_margin

        if line:
            c.drawString(left_margin, y_position, line)
            y_position -= line_height

        # 检查是否需要换页
        if y_position < 50:
            c.showPage()
            c.setFont(font_name, font_size)
            y_position = top_margin

    c.save()
    print(f"PDF已生成: {pdf_path}")
    return pdf_path


def upload_pdf(pdf_path: str) -> str:
    """
    上传PDF文件到ARK服务

    Args:
        pdf_path: PDF文件路径

    Returns:
        上传后的文件ID
    """
    with open(pdf_path, "rb") as f:
        jsonfile = client.files.create(
            file=f,
            purpose="user_data"
        )
    client.files.wait_for_processing(jsonfile.id)
    return jsonfile.id


def upload_video(video_path: str, fps: float = 1) -> str:
    """
    上传视频文件到ARK服务

    Args:
        video_path: 视频文件路径
        fps: 视频采样帧率，默认1

    Returns:
        上传后的文件ID
    """
    with open(video_path, "rb") as f:
        vidofile = client.files.create(
            file=f,
            purpose="user_data",
            preprocess_configs={
                "video": {
                    "fps": fps,
                }
            }
        )
    client.files.wait_for_processing(vidofile.id)
    return vidofile.id


def generate_prompt_from_video(video_file_id: str, json_file_id: str, prompt_text: str = None) -> str:
    """
    根据视频和JSON文件生成提示词

    Args:
        video_file_id: 视频文件ID
        json_file_id: JSON/PDF文件ID
        prompt_text: 自定义提示词，默认要求反推视频提示词并以JSON格式输出

    Returns:
        API响应结果
    """
    if prompt_text is None:
        prompt_text = "反推视频提示词，并以文档中json格式输出"

    response = client.responses.create(
        model="ep-20260820135557-h4kfc",
        input=[
            {"role": "user", "content": [
                {
                    "type": "input_video",
                    "file_id": video_file_id
                },
                {
                    "type": "input_file",
                    "file_id": json_file_id
                },
                {
                    "type": "input_text",
                    "text": prompt_text
                }
            ]},
        ],
    )
    print(response.usage)
    print(response)


    return response.output[0].content[0].text

async def process_video_prompt(video_path: str = None, txt_path: str = None, prompt_text: str = None):
    """
    主函数：处理视频提示词生成

    Args:
        video_path: 视频文件路径，默认使用运行目录下的test.mp4
        txt_path: txt文件路径，默认使用运行目录下的"参考json格式.txt"
        prompt_text: 自定义提示词
    """
    # 设置默认值
    if video_path is None:
        video_path = os.path.join(os.getcwd(), "test.mp4")
    if txt_path is None:
        txt_path = os.path.join(os.getcwd(), "json_example.txt")

    # 转换txt为pdf
    pdf_file = convert_txt_to_pdf(txt_path)

    # 上传文件并获取文件ID
    json_file_id = upload_pdf(pdf_file)
    video_file_id = upload_video(video_path)

    # 生成提示词
    result = generate_prompt_from_video(video_file_id, json_file_id, prompt_text)
    print(result)

    # 清理临时PDF文件
    if os.path.exists(pdf_file):
        os.remove(pdf_file)
        print(f"临时PDF已清理: {pdf_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="视频提示词生成工具")
    parser.add_argument("--video", "-v", type=str, help="视频文件路径")
    parser.add_argument("--txt", "-t", type=str, help="参考txt文件路径")
    parser.add_argument("--prompt", "-p", type=str, help="自定义提示词")
    args = parser.parse_args()

    asyncio.run(process_video_prompt(
        video_path=args.video,
        txt_path=args.txt,
        prompt_text=args.prompt
    ))
