import json
import sys
from collections import OrderedDict

def remove_duplicates(pairs):
    result = OrderedDict()
    for key, value in pairs:
        if key not in result:
            result[key] = value
    return result

def main():
    if len(sys.argv) != 3:
        print("用法: python script.py 输入文件.json 输出文件.json")
        return

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    with open(input_file, 'r', encoding='utf-8') as f:
        json_text = f.read()

    # 使用object_pairs_hook来处理可能的重复键
    data_no_duplicates = json.loads(json_text, object_pairs_hook=remove_duplicates)

    # 将结果保存到输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data_no_duplicates, f, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    main()
