'''
Description: 将知乎专栏文章转换为 Markdown 文件保存到本地
Version: 3.0
Author: Glenn
Email: chenluda01@gmail.com
Date: 2024-04-29 14:00:20
FilePath: main.py
Copyright (c) 2023 by Kust-BME, All Rights Reserved. 
'''
import os
import re
import urllib.parse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from urllib.parse import unquote, urlparse, parse_qs
from tqdm import tqdm
import json

def insert_new_line(soup, element, num_breaks):
    """
    在指定位置插入换行符
    """
    for _ in range(num_breaks):
        new_line = soup.new_tag('br')
        element.insert_after(new_line)


def get_article_date(soup):
    """
    从页面中提取文章日期
    """
    date_element = soup.select_one("div.ContentItem-time")
    if date_element:
        match = re.search(r"\d{4}-\d{2}-\d{2}", date_element.get_text())
        if match:
            return match.group().replace('-', '')
    return "Unknown"


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


def download_video(url, save_path):
    """
    从指定url下载视频并保存到本地
    """
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


def judge_zhihu_type(url, cookies=None, session=None, hexo_uploader=False):
    """
    判断url类型
    """
    if session is None:
        session = requests.Session()
        user_agents = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        headers = {
            'User-Agent': user_agents,
            'Accept-Language': 'en,zh-CN;q=0.9,zh;q=0.8',
            'Cookie': cookies
        }
        session.headers.update(headers)

    if url.find("column") != -1:
        # 如果是专栏
        title = parse_zhihu_column(url, session, hexo_uploader)

    elif url.find("answer") != -1:
        # 如果是回答
        title = parse_zhihu_answer(url, session, hexo_uploader)

    elif url.find("zvideo") != -1:
        # 如果是视频
        title = parse_zhihu_zvideo(url, session, hexo_uploader)

    else:
        # 如果是单篇文章
        title = parse_zhihu_article(url, session, hexo_uploader)

    return title


def save_and_transform(title_element, content_element, author, url, hexo_uploader, soup, date=None):
    """
    转化并保存为 Markdown 格式文件
    """
    # 获取标题和内容
    if title_element is not None:
        title = title_element.text.strip()
    else:
        title = "Untitled"

    # 防止文件名称太长，加载不出图像
    # markdown_title = get_valid_filename(title[-20:-1])
    # 如果觉得文件名太怪不好管理，那就使用全名
    markdown_title = get_valid_filename(title)

    if date:
        markdown_title = f"({date}){markdown_title}_{author}"
    else:
        markdown_title = f"{markdown_title}_{author}"

    if content_element is not None:
        # 将 css 样式移除
        for style_tag in content_element.find_all("style"):
            style_tag.decompose()

        for img_lazy in content_element.find_all("img", class_=lambda x: 'lazy' in x if x else True):
            img_lazy.decompose()

        # 处理内容中的标题
        for header in content_element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            header_level = int(header.name[1])  # 从标签名中获取标题级别（例如，'h2' -> 2）
            header_text = header.get_text(strip=True)  # 提取标题文本
            # 转换为 Markdown 格式的标题
            markdown_header = f"{'#' * header_level} {header_text}"
            insert_new_line(soup, header, 1)
            header.replace_with(markdown_header)

        # 处理回答中的图片
        for img in content_element.find_all("img"):
            if 'src' in img.attrs:
                img_url = img.attrs['src']
            else:
                continue

            img_name = urllib.parse.quote(os.path.basename(img_url))
            img_path = f"{markdown_title}/{img_name}"

            extensions = ['.jpg', '.png', '.gif']  # 可以在此列表中添加更多的图片格式

            # 如果图片链接中图片后缀后面还有字符串则直接截停
            for ext in extensions:
                index = img_path.find(ext)
                if index != -1:
                    img_path = img_path[:index + len(ext)]
                    break  # 找到第一个匹配的格式后就跳出循环

            img["src"] = img_path

            # 下载图片并保存到本地
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            download_image(img_url, img_path)

            # 在图片后插入换行符
            insert_new_line(soup, img, 1)

        # 在图例后面加上换行符
        for figcaption in content_element.find_all("figcaption"):
            insert_new_line(soup, figcaption, 2)

        # 处理链接
        for link in content_element.find_all("a"):
            if 'href' in link.attrs:
                original_url = link.attrs['href']

                # 解析并解码 URL
                parsed_url = urlparse(original_url)
                query_params = parse_qs(parsed_url.query)
                target_url = query_params.get('target', [original_url])[
                    0]  # 使用原 URL 作为默认值
                article_url = unquote(target_url)  # 解码 URL

                # 如果没有 data-text 属性，则使用文章链接作为标题
                if 'data-text' not in link.attrs:
                    article_title = article_url
                else:
                    article_title = link.attrs['data-text']

                markdown_link = f"[{article_title}]({article_url})"

                link.replace_with(markdown_link)

        # 提取并存储数学公式
        math_formulas = []
        math_tags = []
        for math_span in content_element.select("span.ztext-math"):
            latex_formula = math_span['data-tex']
            # math_formulas.append(latex_formula)
            # math_span.replace_with("@@MATH@@")
            # 使用特殊标记标记位置
            if latex_formula.find("\\tag") != -1:
                math_tags.append(latex_formula)
                insert_new_line(soup, math_span, 1)
                math_span.replace_with("@@MATH_FORMULA@@")
            else:
                math_formulas.append(latex_formula)
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

        for formula in math_tags:
            if hexo_uploader:
                content = content.replace(
                    "@@MATH\_FORMULA@@",
                    "$$" + "{% raw %}" + formula + "{% endraw %}" + "$$",
                    1,
                )
            else:
                # 如果公式中包含 $ 则不再添加 $ 符号
                if formula.find("$") != -1:
                    content = content.replace(
                        "@@MATH\_FORMULA@@", f"{formula}", 1)
                else:
                    content = content.replace(
                        "@@MATH\_FORMULA@@", f"$${formula}$$", 1)

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


def parse_zhihu_zvideo(url, session, hexo_uploader):
    """
    解析知乎视频并保存为 Markdown 格式文件
    """
    try:
        response = session.get(url)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred: {err}")
        return None
    except requests.exceptions.RequestException as err:
        print(f"Error occurred: {err}")
        return None

    soup = BeautifulSoup(response.content, "html.parser")
    if soup.text.find("有问题，就会有答案打开知乎App在「我的页」右上角打开扫一扫其他扫码方式") != -1:
        print("Cookies are required to access the article.")
        return None
    if soup.text.find("你似乎来到了没有知识存在的荒原") != -1:
        print("The page does not exist.")
        return None
    data = json.loads(soup.select_one("div.ZVideo-video")['data-zop'])

    match = re.search(r"\d{4}-\d{2}-\d{2}",
                      soup.select_one("div.ZVideo-meta").text)
    if match:
        # 将日期中的"-"替换为空字符以格式化为YYYYMMDD
        date = match.group().replace('-', '')
    else:
        date = "Unknown"

    markdown_title = f"({date}){data['authorName']}_{data['title']}/{data['authorName']}_{data['title']}.mp4"

    video_url = None
    script = soup.find('script', id='js-initialData')
    if script:
        data = json.loads(script.text)
        try:
            videos = data['initialState']['entities']['zvideos']
            for video_id, video_info in videos.items():
                if 'playlist' in video_info['video']:
                    for quality, details in video_info['video']['playlist'].items():
                        video_url = details['playUrl']
        except KeyError as e:
            print("Key error in parsing JSON data:", e)
            return None
    else:
        print("No suitable script tag found for video data")
        return None

    os.makedirs(os.path.dirname(markdown_title), exist_ok=True)

    download_video(video_url, markdown_title)

    return markdown_title


def parse_zhihu_article(url, session, hexo_uploader):
    """
    解析知乎文章并保存为Markdown格式文件
    """
    try:
        response = session.get(url)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred: {err}")
        return None
    except requests.exceptions.RequestException as err:
        print(f"Error occurred: {err}")
        return None

    soup = BeautifulSoup(response.content, "html.parser")
    if soup.text.find("有问题，就会有答案打开知乎App在「我的页」右上角打开扫一扫其他扫码方式") != -1:
        print("Cookies are required to access the article.")
        return None
    if soup.text.find("你似乎来到了没有知识存在的荒原") != -1:
        print("The page does not exist.")
        return None
    title_element = soup.select_one("h1.Post-Title")
    content_element = soup.select_one("div.Post-RichTextContainer")
    date = get_article_date(soup)
    author = soup.select_one('div.AuthorInfo').find(
        'meta', {'itemprop': 'name'}).get('content')

    markdown_title = save_and_transform(
        title_element, content_element, author, url, hexo_uploader, soup, date)

    return markdown_title


def parse_zhihu_answer(url, session, hexo_uploader):
    """
    解析知乎回答并保存为 Markdown 格式文件
    """
    try:
        response = session.get(url)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred: {err}")
        return None
    except requests.exceptions.RequestException as err:
        print(f"Error occurred: {err}")
        return None

    # 解析HTML
    soup = BeautifulSoup(response.content, "html.parser")
    if soup.text.find("有问题，就会有答案打开知乎App在「我的页」右上角打开扫一扫其他扫码方式") != -1:
        print("Cookies are required to access the article.")
        return None
    if soup.text.find("你似乎来到了没有知识存在的荒原") != -1:
        print("The page does not exist.")
        return None
    # 找到回答标题、内容、作者所在的元素
    title_element = soup.select_one("h1.QuestionHeader-title")
    content_element = soup.select_one("div.RichContent-inner")
    date = get_article_date(soup)
    author = soup.select_one('div.AuthorInfo').find(
        'meta', {'itemprop': 'name'}).get('content')

    # 解析知乎文章并保存为Markdown格式文件
    markdown_title = save_and_transform(
        title_element, content_element, author, url, hexo_uploader, soup, date)

    return markdown_title


def load_processed_articles(filename):
    """
    从文件加载已处理文章的ID。
    """
    if not os.path.exists(filename):
        return set()
    with open(filename, 'r', encoding='utf-8') as file:
        return set(file.read().splitlines())


def save_processed_article(filename, article_id):
    """
    将处理过的文章ID保存到文件。
    """
    with open(filename, 'a', encoding='utf-8') as file:
        file.write(article_id + '\n')


def parse_zhihu_column(url, session, hexo_uploader):
    """
    解析知乎专栏并保存为 Markdown 格式文件
    """
    try:
        response = session.get(url)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred: {err}")
        return None
    except requests.exceptions.RequestException as err:
        print(f"Error occurred: {err}")
        return None

    # 解析HTML
    soup = BeautifulSoup(response.content, "html.parser")

    # 将所有文章放在一个以专栏标题命名的文件夹中
    title = soup.text.split('-')[0].strip()
    folder_name = get_valid_filename(title)
    os.makedirs(folder_name, exist_ok=True)
    os.chdir(folder_name)

    processed_filename = "processed_articles.txt"
    processed_articles = load_processed_articles(processed_filename)

    # 获取所有文章链接
    url_template = "https://zhuanlan.zhihu.com/p/{id}"
    offset = 0
    total_parsed = 0

    # 首先获取总文章数
    api_url = f"/api/v4/columns/{url.split('/')[-1]}/items?limit=1&offset=0"
    response = requests.get(f"https://www.zhihu.com{api_url}")
    total_articles = response.json()["paging"]["totals"]

    # 计算已处理的文章数
    already_processed = len(processed_articles)

    # 初始化进度条，从已处理的文章数开始
    progress_bar = tqdm(total=total_articles,
                        initial=already_processed, desc="解析文章")

    while True:
        api_url = f"/api/v4/columns/{url.split('/')[-1]}/items?limit=10&offset={offset}"
        response = session.get(f"https://www.zhihu.com{api_url}")
        data = response.json()

        for item in data["data"]:
            if item["type"] == "zvideo":
                video_id = str(item["id"])
                if video_id in processed_articles:
                    continue

                video_link = f"https://www.zhihu.com/zvideo/{video_id}"
                judge_zhihu_type(video_link, None, session, hexo_uploader)
                save_processed_article(processed_filename, video_id)
                progress_bar.update(1)  # 更新进度条

            else:
                article_id = str(item["id"])
                if article_id in processed_articles:
                    continue

                article_link = url_template.format(id=article_id)
                judge_zhihu_type(article_link, None, session, hexo_uploader)
                save_processed_article(processed_filename, article_id)
                progress_bar.update(1)  # 更新进度条

        if data["paging"]["is_end"]:
            break

        offset += 10

    progress_bar.close()  # 完成后关闭进度条
    os.remove(processed_filename)  # 删除已处理文章的ID文件
    return folder_name


if __name__ == "__main__":
    
    cookies = 'your_zhihu_cookies'

    # 回答
    # url = "https://www.zhihu.com/question/362131975/answer/2182682685"

    # 文章
    # url = "https://zhuanlan.zhihu.com/p/545645937"

    # 视频
    # url = "https://www.zhihu.com/zvideo/1493715983701831680"

    # 专栏
    url = "https://www.zhihu.com/column/c_1104714416238673920"

    # hexo_uploader=True 表示在公式前后加上 {% raw %} {% endraw %}，以便 hexo 正确解析
    judge_zhihu_type(url, cookies, hexo_uploader=False)
