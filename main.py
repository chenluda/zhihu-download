'''
Description: 将知乎专栏文章转换为 Markdown 文件保存到本地
Version: 1.0
Author: Glenn
Email: chenluda01@outlook.com
Date: 2023-06-12 19:58:39
FilePath: main.py
Copyright (c) 2023 by Kust-BME, All Rights Reserved. 
'''
import os
import re
import urllib.parse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md


def download_image(url, save_path):
    """
    从指定url下载图片并保存到本地
    """
    if url.startswith("data:image/"):
        # 如果链接以 "data:" 开头，则直接写入数据到文件
        with open(save_path, "wb") as f:
            f.write(url.split(",", 1)[1].encode("utf-8"))
    else:
        response = requests.get(url)
        with open(save_path, "wb") as f:
            f.write(response.content)


def get_valid_filename(s):
    """
    将字符串转换为有效的文件名
    """
    # 检查第一个字符是否为特殊符号或数字
    if s and (not s[0].isalpha() or s[0].isdigit()):
        s = s[1:]
    s = str(s).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w_]', '', s)


def judge_zhihu_type(url, hexo_uploader=False):
    """
    判断url类型
    """
    if url.find("column") != -1:
        # 如果是专栏
        title = parse_zhihu_column(url, hexo_uploader)

    elif url.find("answer") != -1:
        # 如果是回答
        title = parse_zhihu_answer(url, hexo_uploader)

    else:
        # 如果是单篇文章
        title = parse_zhihu_article(url, hexo_uploader)

    return title


def save_and_transform(title_element, content_element, author, url, hexo_uploader):
    """
    转化并保存为 Markdown 格式文件
    """
    # 获取标题和内容
    if title_element is not None:
        title = title_element.text.strip()
    else:
        title = "Untitled"
    # 防止文件名称太长，加载不出图像
    markdown_title = get_valid_filename(title[-20:-1])
    markdown_title = f"{markdown_title}_{author}"

    if content_element is not None:
        # 将 css 样式移除
        for style_tag in content_element.find_all("style"):
            style_tag.decompose()

        for img_lazy in content_element.find_all("img", class_=lambda x: 'lazy' in x if x else True):
            img_lazy.decompose()

        # 处理回答中的图片
        for img in content_element.find_all("img"):
            # 将图片链接替换为本地路径
            img_url = img.get("data-original", img.get("src", None))
            if img_url is None:
                continue

            img_name = urllib.parse.quote(os.path.basename(img_url))
            img_path = f"{markdown_title}/{img_name}"

            # 如果图片链接中 .jpg 后面还有字符串则直接截停
            if img_path.find('.jpg') + 3 != len(img_path) - 1:
                img_path = img_path[0: img_path.find('.jpg') + 4]

            img["src"] = img_path

            # 下载图片并保存到本地
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            download_image(img_url, img_path)

            # 在图片后插入换行符
            img.insert_after('\n\n')

        # 在 </figcaption> 后面加上换行符
        for figcaption in content_element.find_all("figcaption"):
            figcaption.insert_after('\n\n')

        # 处理卡片链接
        for card_link in content_element.find_all("a", class_="LinkCard"):
            article_url = card_link['href']
            article_title = card_link['data-text']
            
            # 如果没有标题，则使用span代替
            if not article_title:
                article_title_span = card_link.select_one(".LinkCard-title")
                if article_title_span:
                    article_title = article_title_span.text.strip()
                else:
                    article_title = article_url # 如果没有span，则使用链接代替
            
            markdown_link = f"[{article_title}]({article_url})"
            card_link.insert_after('\n\n')
            card_link.replace_with(markdown_link)

        # 提取并存储数学公式
        math_formulas = []
        for math_span in content_element.select("span.ztext-math"):
            latex_formula = math_span['data-tex']
            math_formulas.append(latex_formula)
            # 使用特殊标记标记位置
            math_span.replace_with("@@MATH@@")

        # 获取文本内容
        content = content_element.decode_contents().strip()
        # 转换为 markdown
        content = md(content)

        # 将特殊标记替换为 LaTeX 数学公式
        for formula in math_formulas:
            if hexo_uploader:
                content = content.replace(
                    "@@MATH@@", "$" + "{% raw %}" + formula + "{% endraw %}" + "$", 1)
            else:
                # 如果公式中包含 $ 则不再添加 $ 符号
                if formula.find('$') != -1:
                    content = content.replace("@@MATH@@", f"{formula}", 1)
                else:
                    content = content.replace("@@MATH@@", f"${formula}$", 1)

    else:
        content = ""

    # 转化为 Markdown 格式
    if content:
        markdown = f"# {title}\n\n **Author:** [{author}]\n\n **Link:** [{url}]\n\n{content}"
    else:
        markdown = f"# {title}\n\n Content is empty."

    # 保存 Markdown 文件
    with open(f"{markdown_title}.md", "w", encoding="utf-8") as f:
        f.write(markdown)

    return markdown_title


def parse_zhihu_article(url, hexo_uploader):
    """
    解析知乎文章并保存为Markdown格式文件
    """
    # 发送GET请求获取网页内容
    response = requests.get(url)
    # 解析HTML
    soup = BeautifulSoup(response.content, "html.parser")
    # 找到文章标题和内容所在的元素
    title_element = soup.select_one("h1.Post-Title")
    content_element = soup.select_one("div.Post-RichTextContainer")
    author = soup.select_one('div.AuthorInfo').find(
        'meta', {'itemprop': 'name'}).get('content')

    # 解析知乎文章并保存为Markdown格式文件
    markdown_title = save_and_transform(
        title_element, content_element, author, url, hexo_uploader)

    return markdown_title


def parse_zhihu_answer(url, hexo_uploader):
    """
    解析知乎回答并保存为 Markdown 格式文件
    """
    # 发送GET请求获取网页内容
    response = requests.get(url)
    # 解析HTML
    soup = BeautifulSoup(response.content, "html.parser")
    # 找到回答标题、内容、作者所在的元素
    title_element = soup.select_one("h1.QuestionHeader-title")
    content_element = soup.select_one("div.RichContent-inner")
    author = soup.select_one('div.AuthorInfo').find(
        'meta', {'itemprop': 'name'}).get('content')

    # 解析知乎文章并保存为Markdown格式文件
    markdown_title = save_and_transform(
        title_element, content_element, author, url, hexo_uploader)

    return markdown_title


def parse_zhihu_column(url, hexo_uploader):
    """
    解析知乎专栏并获取所有文章链接
    """
    # 发送GET请求获取网页内容
    response = requests.get(url)
    # 解析HTML
    soup = BeautifulSoup(response.content, "html.parser")

    # 将所有文章放在一个以专栏标题命名的文件夹中
    title = soup.text.split('-')[0].strip()
    folder_name = get_valid_filename(title)
    os.makedirs(folder_name, exist_ok=True)
    os.chdir(folder_name)

    # 获取所有文章链接
    items = []
    url_template = "https://zhuanlan.zhihu.com/p/{id}"
    offset = 0
    while True:
        api_url = f"/api/v4/columns/{url.split('/')[-1]}/items?limit=10&offset={offset}"
        response = requests.get(f"https://www.zhihu.com{api_url}")
        data = response.json()
        items += data["data"]
        if data["paging"]["is_end"]:
            break
        offset += 10

    article_links = [url_template.format(id=item["id"]) for item in items]

    # 遍历所有文章链接，转换为Markdown并保存到本地
    for article_link in article_links:
        parse_zhihu_article(article_link, hexo_uploader)

    return folder_name


if __name__ == "__main__":

    # 回答
    # url = "https://www.zhihu.com/question/35931336/answer/2996939350"

    # 文章
    url = "https://zhuanlan.zhihu.com/p/618270933"

    # 专栏
    # url = "https://www.zhihu.com/column/c_1649842617335672832"

    # hexo_uploader=True 表示在公式前后加上 {% raw %} {% endraw %}，以便 hexo 正确解析
    judge_zhihu_type(url, hexo_uploader=False)
