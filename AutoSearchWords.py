#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import requests
from bs4 import BeautifulSoup

# ---------- 配置 ----------
DEFAULT_OUTPUT = "英语/单词本.md"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
BING_DICT_URL = "https://global.bing.com/dict/search"


# ---------- 解析函数 ----------
def fetch_definition(word):
    """从 Bing 词典获取单词释义，返回释义字符串。"""
    params = {"q": word}
    headers = {"User-Agent": USER_AGENT}

    try:
        resp = requests.get(BING_DICT_URL, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"请求失败: {e}", file=sys.stderr)
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    qdef = soup.find("div", class_="qdef")
    if not qdef:
        print(f"未找到单词 '{word}' 的释义。", file=sys.stderr)
        return None

    ul = qdef.find("ul")
    if not ul:
        print("未找到释义列表，可能页面结构变化。", file=sys.stderr)
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
        print("未提取到有效释义。", file=sys.stderr)
        return None

    return "；".join(definitions)


# ---------- 文件初始化 / 修复 ----------
def ensure_initialized(output_file):
    """
    确保单词本文件存在且表头完整（标题 + 列名 + 分隔行）。
    若文件不存在则创建，若表头不完整则修复。
    返回 True 表示进行了创建/修复操作。
    """
    header_title = "# 单词本\n"
    header_sep = "|单词|释义|次数|备注|\n"
    header_divider = "|:--|:--|:--|:--|\n"
    full_header = header_title + header_sep + header_divider

    if not os.path.exists(output_file):
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(full_header)
        print(f"已自动创建单词本文件：{output_file}")
        return True
    else:
        with open(output_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 检查是否至少有三行且格式正确
        if len(lines) >= 3 and lines[0].strip().startswith("# 单词本") and \
           lines[1].strip() == "|单词|释义|次数|备注|" and \
           lines[2].strip() == "|:--|:--|:--|:--|":
            return False
        else:
            # 提取数据行（跳过所有可能的表头行）
            data_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("# 单词本") or \
                   stripped == "|单词|释义|次数|备注|" or \
                   stripped == "|:--|:--|:--|:--|":
                    continue
                data_lines.append(line)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(full_header)
                f.writelines(data_lines)
            print(f"已修复文件 '{output_file}' 的表头。")
            return True


def init_file(output_file):
    """手动初始化（--init），若文件已存在则提示。"""
    if os.path.exists(output_file):
        print(f"文件 '{output_file}' 已存在，无需初始化。", file=sys.stderr)
        sys.exit(1)
    else:
        ensure_initialized(output_file)
        print(f"已初始化单词本文件：{output_file}")


# ---------- 更新单词（核心修改） ----------
def update_word(output_file, word, meaning):
    """
    更新单词本：
    - 若单词不存在：追加新行，次数为空，放在末尾。
    - 若单词已存在：删除旧行，追加新行（用最新释义，次数递增），放在末尾。
    这样确保最新查询的单词始终在最后一行。
    """
    ensure_initialized(output_file)

    with open(output_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 表头固定为前三行
    header = lines[:3]
    data_lines = lines[3:] if len(lines) > 3 else []

    new_entry = None
    remaining_data = []

    # 遍历数据行，若找到该单词则记录次数并删除该行
    for line in data_lines:
        if line.startswith("|") and not line.startswith("|:--"):
            parts = line.strip().split("|")
            if len(parts) >= 4 and parts[1].strip() == word:
                # 找到旧行，提取次数
                count_str = parts[3].strip()
                if count_str == "":
                    new_count = 2
                else:
                    try:
                        new_count = int(count_str) + 1
                    except ValueError:
                        new_count = 2
                # 构建新行（使用最新释义）
                new_entry = f"|{word}|{meaning}|{new_count}|{parts[4] if len(parts) > 4 else ''}|\n"
                continue  # 跳过该行（不保留）
        remaining_data.append(line)

    if new_entry is None:
        # 单词不存在，首次查询，次数留空
        new_entry = f"|{word}|{meaning}|||\n"

    # 重新组合：原数据（除去旧行）+ 新行（追加到末尾）
    final_data = remaining_data + [new_entry]

    # 写回文件
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(header)
        f.writelines(final_data)

    print(f"已更新单词 '{word}'。")


# ---------- 主程序 ----------
def main():
    # 处理 --init 参数
    if "--init" in sys.argv:
        output_file = DEFAULT_OUTPUT
        init_file(output_file)
        return

    # 正常查询流程
    output_file = DEFAULT_OUTPUT
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]

    # 单次查询
    if len(sys.argv) >= 2 and not sys.argv[1].startswith("--"):
        word = sys.argv[1].strip()
        if not word:
            print("单词不能为空。", file=sys.stderr)
            sys.exit(1)
        meaning = fetch_definition(word)
        if meaning is None:
            sys.exit(1)
        update_word(output_file, word, meaning)
        return

    # 交互模式
    print("进入交互模式，输入单词查询，输入 / 退出，按 Ctrl+C 中断")
    while True:
        try:
            word = input("请输入单词: ").strip()
            if word == "/":
                print("退出程序。")
                break
            if not word:
                continue
            meaning = fetch_definition(word)
            if meaning is None:
                continue
            update_word(output_file, word, meaning)
        except KeyboardInterrupt:
            print("\n用户中断，退出程序。")
            break
        except Exception as e:
            print(f"发生错误: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()