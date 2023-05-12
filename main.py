'''
Description: 将知乎专栏文章转换为 Markdown 文件保存到本地
Version: 1.0
Author: 陈路达
Email: chenluda01@outlook.com
Date: 2023-04-18 10:48:38
FilePath: main.py
Copyright (c) 2022 by Kust-BME, All Rights Reserved. 
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
    s = str(s).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w_]', '', s)


def judge_zhihu_type(url):
    """
    判断url类型
    """
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    if soup.text.find("知乎专栏") != -1:
        # 如果是专栏，将所有文章放在一个以专栏标题命名的文件夹中
        title = soup.text.split('-')[0].strip()
        folder_name = get_valid_filename(title)
        os.makedirs(folder_name, exist_ok=True)
        os.chdir(folder_name)
        parse_zhihu_column(url)

    elif url.find("answer") != -1:
        # 如果是回答
        parse_zhihu_answer(url)
        
    else:
        # 如果是单篇文章
        parse_zhihu_article(url)


def save_and_transform(title_element, content_element, author, url):
    """
    转化并保存为 Markdown 格式文件
    """
    # 获取标题和内容
    if title_element is not None: 
        title = title_element.text.strip()
    else:
        title = "Untitled"
    # 防止文件名称太长，加载不出图像
    markdown_title = get_valid_filename(title)[0:20]
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
            img_path = f"{markdown_title}_files/{img_name}"

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

        # 获取回答文本内容
        content = content_element.decode_contents().strip()
        # 转换为 markdown
        content = md(content)
    else:
        content = ""

    # 转化为 Markdown 格式
    if content:
        markdown = f"# {title}\n\n **Author:** [{author}]\n\n **Link:** [{url}]\n\n{content}"
    else:
        markdown = f"# {title}\n\nContent is empty."

    # 保存 Markdown 文件
    with open(f"{markdown_title}.md", "w", encoding="utf-8") as f:
        f.write(markdown)


def parse_zhihu_article(url):
    """
    解析知乎文章并保存为Markdown格式文件
    """
    # 发送GET请求获取网页内容
    response = requests.get(url)

    # 解析HTML
    soup = BeautifulSoup(response.content, "html.parser")

    # 找到文章标题和内容所在的元素
    title_element = soup.select_one("h1.Post-Title")
    content_element = soup.select_one("div.Post-RichText")
    author = soup.select_one('div.AuthorInfo > div.AuthorInfo-content > div.AuthorInfo-head').text.strip()

    # 解析知乎文章并保存为Markdown格式文件
    save_and_transform(title_element, content_element, author, url)


def parse_zhihu_answer(url):
    """
    解析知乎回答并保存为 Markdown 格式文件
    """
    # 发送 GET 请求获取网页内容
    response = requests.get(url)

    # 解析 HTML
    soup = BeautifulSoup(response.content, "html.parser")

    # 找到回答标题、内容、作者所在的元素
    title_element = soup.select_one("h1.QuestionHeader-title")
    content_element = soup.select_one("div.RichContent-inner")
    author = soup.select_one('div.AuthorInfo > div.AuthorInfo-content > div.AuthorInfo-head').text.strip()

    # 解析知乎文章并保存为Markdown格式文件
    save_and_transform(title_element, content_element, author, url)


def parse_zhihu_column(url):
    """
    解析知乎专栏并获取所有文章链接
    """
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
        parse_zhihu_article(article_link)


if __name__=="__main__":

    # 回答
    # url = "https://www.zhihu.com/question/593914819/answer/2971671307"

    # 文章
    # url = "https://zhuanlan.zhihu.com/p/626703154"

    # 专栏
    url = "https://www.zhihu.com/column/c_1620937636624703488"

    judge_zhihu_type(url)
