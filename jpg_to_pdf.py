import os
from fpdf import FPDF
from PIL import Image

# 图片文件夹路径
folder = r"C:\BaiduNetdiskDownload"
# 输出 PDF 文件
output_pdf = r"C:\BaiduNetdiskDownload\output.pdf"

# 获取所有 JPG/JPEG 文件并排序
images = [f for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg'))]
images.sort()

pdf = FPDF(unit="pt")  # 用 pt 单位，方便转换像素
# 1 pt = 1/72 inch

for img_name in images:
    img_path = os.path.join(folder, img_name)
    image = Image.open(img_path)
    width_px, height_px = image.size

    # 转换为 PDF pt 单位 (1 px ≈ 0.75 pt)
    # 这里假设 96 dpi, 1 pt = 1/72 inch, 1 px = 1/96 inch => px * 0.75 ≈ pt
    width_pt = width_px * 0.75
    height_pt = height_px * 0.75

    # 新增页面，尺寸等于图片尺寸
    pdf.add_page(format=(width_pt, height_pt))
    pdf.image(img_path, x=0, y=0, w=width_pt, h=height_pt)

pdf.output(output_pdf)
print("PDF 已生成:", output_pdf)