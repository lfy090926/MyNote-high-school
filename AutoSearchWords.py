import sys
import requests
from bs4 import BeautifulSoup

# ---------- 配置 ----------
DEFAULT_OUTPUT = "英语/单词本.md"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
BING_DICT_URL = "https://global.bing.com/dict/search"

# ---------- 解析函数 ----------
def fetch_definition(word):
    """
    从 Bing 词典获取单词释义，返回释义字符串（合并所有词性）。
    如果查询失败或未找到，返回 None。
    """
    params = {"q": word}
    headers = {"User-Agent": USER_AGENT}

    try:
        resp = requests.get(BING_DICT_URL, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"请求失败: {e}", file=sys.stderr)
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # 定位主要释义区域：div.qdef 下的 ul
    qdef = soup.find("div", class_="qdef")
    if not qdef:
        print(f"未找到单词 '{word}' 的释义，可能词典中没有该词。", file=sys.stderr)
        return None

    ul = qdef.find("ul")
    if not ul:
        print(f"未找到释义列表，可能页面结构变化。", file=sys.stderr)
        return None

    definitions = []
    for li in ul.find_all("li"):
        pos_span = li.find("span", class_="pos")
        def_span = li.find("span", class_="def")
        if pos_span and def_span:
            pos = pos_span.get_text(strip=True)
            meaning = def_span.get_text(" ", strip=True)
            definitions.append(f"{pos} {meaning}")

    if not definitions:
        print(f"未提取到有效释义。", file=sys.stderr)
        return None

    return "；".join(definitions)


def save_definition(word, meaning, output_file):
    """
    将释义追加到指定文件中，格式为 |<单词>|<释义>|
    如果该单词已存在，则先删除旧行再追加（更新）。
    """
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []

    new_line = f"|{word}|{meaning}|\n"
    word_prefix = f"|{word}|"
    filtered = [line for line in lines if not line.startswith(word_prefix)]
    filtered.append(new_line)

    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(filtered)

    print(f"已保存 '{word}' 的释义到 {output_file}")


def process_word(word, output_file):
    """查询并保存单个单词"""
    meaning = fetch_definition(word)
    if meaning:
        save_definition(word, meaning, output_file)
        return True
    return False


# ---------- 主程序 ----------
def main():
    # 解析参数，确定输出文件
    output_file = DEFAULT_OUTPUT
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]

    # 如果提供了单词参数，单次模式
    if len(sys.argv) >= 2:
        word = sys.argv[1].strip()
        if not word:
            print("单词不能为空。", file=sys.stderr)
            sys.exit(1)
        process_word(word, output_file)
        sys.exit(0)

    # 交互循环模式（无参数）
    print("进入交互模式，输入单词查询，输入 / 退出，按 Ctrl+C 中断")
    while True:
        try:
            word = input("请输入单词: ").strip()
            if word == "/":
                print("退出程序。")
                break
            if not word:
                continue
            process_word(word, output_file)
        except KeyboardInterrupt:
            print("\n用户中断，退出程序。")
            break
        except Exception as e:
            print(f"发生错误: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()