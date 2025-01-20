import os
import re
import urllib.parse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from urllib.parse import unquote, urlparse, parse_qs
from tqdm import tqdm
import json
from utils.util import insert_new_line, get_article_date, download_image, download_video, get_valid_filename


class ZhihuParser:
    def __init__(self, cookies, hexo_uploader=False):
        self.hexo_uploader = hexo_uploader  # 是否为 hexo 博客上传
        self.cookies = cookies  # 登录知乎后的 cookies
        self.session = requests.Session()  # 创建会话
        self.user_agents = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36" # 用户代理
        self.headers = { # 请求头
            'User-Agent': self.user_agents, 
            'Accept-Language': 'en,zh-CN;q=0.9,zh;q=0.8', 
            'Cookie': self.cookies
        }
        self.session.headers.update(self.headers) # 更新会话的请求头
        self.soup = None # 存储页面的 BeautifulSoup 对象

    def check_connect_error(self, target_link):
        """
        检查是否连接错误
        """
        try:
            response = self.session.get(target_link)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(f"HTTP error occurred: {err}")

        except requests.exceptions.RequestException as err:
            print(f"Error occurred: {err}")

        self.soup = BeautifulSoup(response.content, "html.parser")
        if self.soup.text.find("有问题，就会有答案打开知乎App在「我的页」右上角打开扫一扫其他扫码方式") != -1:
            print("Cookies are required to access the article.")

        if self.soup.text.find("你似乎来到了没有知识存在的荒原") != -1:
            print("The page does not exist.")

    def judge_type(self, target_link):
        """
        判断url类型
        """
        if target_link.find("column") != -1:
            # 如果是专栏
            title = self.parse_zhihu_column(target_link)

        elif target_link.find("answer") != -1:
            # 如果是回答
            title = self.parse_zhihu_answer(target_link)

        elif target_link.find("zvideo") != -1:
            # 如果是视频
            title = self.parse_zhihu_zvideo(target_link)

        else:
            # 如果是单篇文章
            title = self.parse_zhihu_article(target_link)

        return title

    def save_and_transform(self, title_element, content_element, author, target_link, date=None):
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
                insert_new_line(self.soup, header, 1)
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
                download_image(img_url, img_path, self.session)

                # 在图片后插入换行符
                insert_new_line(self.soup, img, 1)

            # 在图例后面加上换行符
            for figcaption in content_element.find_all("figcaption"):
                insert_new_line(self.soup, figcaption, 2)

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
                    insert_new_line(self.soup, math_span, 1)
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
                if self.hexo_uploader:
                    content = content.replace(
                        "@@MATH@@", "$" + "{% raw %}" + formula + "{% endraw %}" + "$", 1)
                else:
                    # 如果公式中包含 $ 则不再添加 $ 符号
                    if formula.find('$') != -1:
                        content = content.replace("@@MATH@@", f"{formula}", 1)
                    else:
                        content = content.replace(
                            "@@MATH@@", f"${formula}$", 1)

            for formula in math_tags:
                if self.hexo_uploader:
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
            markdown = f"# {title}\n\n **Author:** [{author}]\n\n **Link:** [{target_link}]\n\n{content}"
        else:
            markdown = f"# {title}\n\n Content is empty."

        # 保存 Markdown 文件
        with open(f"{markdown_title}.md", "w", encoding="utf-8") as f:
            f.write(markdown)

        return markdown_title

    def parse_zhihu_zvideo(self, target_link):
        """
        解析知乎视频并保存为 Markdown 格式文件
        """
        self.check_connect_error(target_link)
        data = json.loads(self.soup.select_one(
            "div.ZVideo-video")['data-zop'])  # 获取视频数据

        # match = re.search(r"\d{4}-\d{2}-\d{2}",
        #                   soup.select_one("div.ZVideo-meta").text) # 获取日期

        # if match:
        #     # 将日期中的"-"替换为空字符以格式化为YYYYMMDD
        #     date = match.group().replace('-', '')
        # else:
        #     date = "Unknown"

        date = get_article_date(self.soup, "div.ZVideo-meta")

        markdown_title = f"({date}){data['authorName']}_{data['title']}/{data['authorName']}_{data['title']}.mp4"

        video_url = None
        script = self.soup.find('script', id='js-initialData')
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

        download_video(video_url, markdown_title, self.session)

        return markdown_title

    def parse_zhihu_article(self, target_link):
        """
        解析知乎文章并保存为Markdown格式文件
        """
        self.check_connect_error(target_link)
        title_element = self.soup.select_one("h1.Post-Title")
        content_element = self.soup.select_one("div.Post-RichTextContainer")
        date = get_article_date(self.soup, "div.ContentItem-time")
        author = self.soup.select_one('div.AuthorInfo').find(
            'meta', {'itemprop': 'name'}).get('content')

        markdown_title = self.save_and_transform(
            title_element, content_element, author, target_link, date)

        return markdown_title

    def parse_zhihu_answer(self, target_link):
        """
        解析知乎回答并保存为 Markdown 格式文件
        """
        self.check_connect_error(target_link)
        # 找到回答标题、内容、作者所在的元素
        title_element = self.soup.select_one("h1.QuestionHeader-title")
        content_element = self.soup.select_one("div.RichContent-inner")
        date = get_article_date(self.soup, "div.ContentItem-time")
        author = self.soup.select_one('div.AuthorInfo').find(
            'meta', {'itemprop': 'name'}).get('content')

        # 解析知乎文章并保存为Markdown格式文件
        markdown_title = self.save_and_transform(
            title_element, content_element, author, target_link, date)

        return markdown_title

    def load_processed_articles(self, filename):
        """
        从文件加载已处理文章的ID。
        """
        if not os.path.exists(filename):
            return set()
        with open(filename, 'r', encoding='utf-8') as file:
            return set(file.read().splitlines())

    def save_processed_article(self, filename, article_id):
        """
        将处理过的文章ID保存到文件。
        """
        with open(filename, 'a', encoding='utf-8') as file:
            file.write(article_id + '\n')

    def parse_zhihu_column(self, target_link):
        """
        解析知乎专栏并保存为 Markdown 格式文件
        """
        self.check_connect_error(target_link)

        # 将所有文章放在一个以专栏标题命名的文件夹中
        title = self.soup.text.split('-')[0].strip()
        total_articles = int(self.soup.text.split(
            '篇内容')[0].split('·')[-1].strip())  # 总文章数
        folder_name = get_valid_filename(title)
        os.makedirs(folder_name, exist_ok=True)
        os.chdir(folder_name)

        processed_filename = "zhihu_processed_articles.txt"
        processed_articles = self.load_processed_articles(processed_filename)

        # 获取所有文章链接
        offset = 0
        total_parsed = 0

        # # 首先获取总文章数
        # api_url = f"/api/v4/columns/{target_link.split('/')[-1]}/items?limit=1&offset=0"
        # response = session.get(f"https://www.zhihu.com{api_url}")
        # total_articles = response.json()["paging"]["totals"]

        # 计算已处理的文章数
        already_processed = len(processed_articles)

        # 初始化进度条，从已处理的文章数开始
        progress_bar = tqdm(total=total_articles,
                            initial=already_processed, desc="解析文章")

        while True:
            api_url = f"/api/v4/columns/{target_link.split('/')[-1]}/items?limit=10&offset={offset}"
            response = self.session.get(f"https://www.zhihu.com{api_url}")
            data = response.json()

            for item in data["data"]:
                if item["type"] == "zvideo":
                    video_id = str(item["id"])
                    if video_id in processed_articles:
                        continue

                    video_link = f"https://www.zhihu.com/zvideo/{video_id}"
                    self.parse_zhihu_zvideo(video_link)
                    self.save_processed_article(processed_filename, video_id)
                    progress_bar.update(1)  # 更新进度条

                elif item["type"] == "article":
                    article_id = str(item["id"])
                    if article_id in processed_articles:
                        continue

                    article_link = f"https://zhuanlan.zhihu.com/p/{article_id}"
                    self.parse_zhihu_article(article_link)
                    self.save_processed_article(processed_filename, article_id)
                    progress_bar.update(1)  # 更新进度条
                
                elif item["type"] == "answer":
                    answer_id = str(item["id"])
                    if answer_id in processed_articles:
                        continue

                    answer_link = f"https://www.zhihu.com/question/{item['question']['id']}/answer/{answer_id}"
                    self.judge_type(answer_link)
                    self.save_processed_article(processed_filename, answer_id)
                    progress_bar.update(1)

            if data["paging"]["is_end"]:
                break

            offset += 10

        progress_bar.close()  # 完成后关闭进度条
        os.remove(processed_filename)  # 删除已处理文章的ID文件
        return folder_name


if __name__ == "__main__":
    cookies = "your cookies here"

    # 回答
    # url = "https://www.zhihu.com/question/362131975/answer/2182682685"

    # 文章
    # url = "https://zhuanlan.zhihu.com/p/8026034992"

    # 视频
    # url = "https://www.zhihu.com/zvideo/1493715983701831680"

    # 专栏
    url = "https://www.zhihu.com/column/c_1796502192443777024"

    # hexo_uploader=True 表示在公式前后加上 {% raw %} {% endraw %}，以便 hexo 正确解析
    parser = ZhihuParser(cookies)
    parser.judge_type(url)
