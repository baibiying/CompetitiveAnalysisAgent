from agent import analyze_product

if __name__ == "__main__":
    # 请将此处图片路径替换为你本地的测试图片路径
    test_image_path = "fruit.jpg"
    result = analyze_product(test_image_path)
    print("分析结果：")
    print(result) 