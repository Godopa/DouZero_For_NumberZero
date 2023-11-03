from PIL import Image


def crop_image_by_coordinates(input_path, output_path, x1, y1, x2, y2):
    """
    根据指定的坐标位置裁剪图片并保存。

    参数：
    input_path（str）：输入图片的文件路径。
    output_path（str）：裁剪后图片的保存路径。
    x1（int）：左上角点的x坐标。
    y1（int）：左上角点的y坐标。
    x2（int）：右下角点的x坐标。
    y2（int）：右下角点的y坐标。
    """
    try:
        # 打开输入图片
        image = Image.open(input_path)

        # 裁剪图片
        cropped_image = image.crop((x1, y1, x2, y2))

        # 保存裁剪后的图片
        cropped_image.save(output_path)
        print("图片裁剪成功，已保存到", output_path)
    except Exception as e:
        print("图片裁剪失败：", str(e))


# 使用示例
input_path = "D:\\Users\\Administrator\\Pictures\\screenshot\\1698865313299.jpg"  # 输入图片文件路径
x1, y1 = 393, 800  # 左上角点的坐标
x2, y2 = 443, 860  # 右下角点的坐标
x = 61.5
test = 0
while x2 < 1920:
    test = test + 1
    output_path = "D:\\Users\\Administrator\\Pictures\\screenshot\\test" + str(test) + ".png"  # 裁剪后图片保存路径
    crop_image_by_coordinates(input_path, output_path, x1, y1, x2, y2)
    x1 = x1 + x
    x2 = x2 + x
