import os
import re
import urllib.parse
import logging
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from urllib.parse import unquote, urlparse, parse_qs
from tqdm import tqdm
import json
from utils.util import insert_new_line, get_article_date, download_image, download_video, get_valid_filename, get_article_date_weixin


class WeixinParser:
    def __init__(self, hexo_uploader=False, keep_logs=False):
        self.hexo_uploader = hexo_uploader
        self.session = requests.Session()
        self.keep_logs = keep_logs
        self.user_agents = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        self.headers = {
            'User-Agent': self.user_agents,
            'Accept-Language': 'en,zh-CN;q=0.9,zh;q=0.8',
        }
        self.session.headers.update(self.headers)
        self.soup = None
        self.logger = logging.getLogger('weixin_parser')
        
        if self.keep_logs:
            self.logger.setLevel(logging.INFO)
            if not self.logger.handlers and not os.path.exists('./logs'):
                os.makedirs('./logs', exist_ok=True)
            
            if not self.logger.handlers:
                handler = logging.FileHandler(
                    './logs/weixin_download.log', encoding='utf-8')
                formatter = logging.Formatter(
                    '%(asctime)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
        else:
            self.logger.setLevel(logging.CRITICAL + 1)

    def log(self, level, message):
        """自定义日志函数，只在keep_logs为True时记录"""
        if self.keep_logs:
            if level == 'info':
                self.logger.info(message)
            elif level == 'warning':
                self.logger.warning(message)
            elif level == 'error':
                self.logger.error(message)

    def check_connect_error(self, target_link):
        """
        检查是否连接错误
        """
        try:
            response = self.session.get(target_link)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            self.log('error', f"HTTP error occurred: {err}")
            raise
        except requests.exceptions.RequestException as err:
            self.log('error', f"Error occurred: {err}")
            raise

        self.soup = BeautifulSoup(response.content, "html.parser")

    def judge_type(self, target_link):
        """
        判断url类型
        """
        try:
            title = self.parse_article(target_link)
            return title
        except Exception as e:
            self.log('error', f"Error processing URL {target_link}: {str(e)}")
            raise

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

            # 处理内容中的标题
            for header in content_element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                header_level = int(header.name[1])  # 从标签名中获取标题级别（例如，'h2' -> 2）
                header_text = header.get_text(strip=True)  # 提取标题文本
                # 转换为 Markdown 格式的标题
                markdown_header = f"{'#' * header_level} {header_text}"
                insert_new_line(self.soup, header, 1)
                header.replace_with(markdown_header)

            img_index = 0
            # 处理回答中的图片
            for img in content_element.find_all("img"):
                try:
                    if 'data-src' in img.attrs:
                        img_url = img.attrs['data-src']
                    elif 'src' in img.attrs:
                        img_url = img.attrs['src']
                    else:
                        continue

                    # 解析URL并获取查询参数
                    parsed_url = urllib.parse.urlparse(img_url)
                    query_params = urllib.parse.parse_qs(parsed_url.query)

                    # 确定图片扩展名，优先从查询参数中获取
                    if 'wx_fmt' in query_params:
                        ext = f".{query_params['wx_fmt'][0]}"
                    else:
                        # 如果没有查询参数，则尝试从路径部分获取扩展名
                        ext = os.path.splitext(parsed_url.path)[1] or '.jpg'  # 默认使用.jpg

                    # 提取图片格式
                    img_name = f"img_{img_index:02d}{ext}"
                    img_path = f"{markdown_title}/{img_name}"

                    img["src"] = img_path

                    # 下载图片并保存到本地
                    os.makedirs(os.path.dirname(img_path), exist_ok=True)
                    download_image(img_url, img_path, self.session)

                    img_index += 1

                    # 在图片后插入换行符
                    insert_new_line(self.soup, img, 1)
                except Exception as e:
                    self.log('warning', f"Error downloading image {img.get('data-src', img.get('src', 'unknown'))}: {str(e)}")
                    # 继续处理下一张图片，不中断进程

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

    def parse_article(self, target_link):
        """
        解析知乎文章并保存为Markdown格式文件
        """
        try:
            self.check_connect_error(target_link)

            title_element = self.soup.select_one("h1#activity-name")
            content_element = self.soup.select_one("div#js_content")
            
            if not title_element or not content_element:
                self.log('warning', "Could not find title or content elements")
                if not title_element:
                    self.log('warning', "Missing title element")
                if not content_element:
                    self.log('warning', "Missing content element")

            date = get_article_date_weixin(self.soup.find_all('script', type='text/javascript'))
            
            author_element = self.soup.select_one("div#meta_content")
            if author_element and author_element.find_all("a"):
                author = author_element.find_all("a")[0].text.strip()
            else:
                author = "未知作者"
                self.log('warning', "Could not find author information")

            markdown_title = self.save_and_transform(
                title_element, content_element, author, target_link, date)
                
            self.log('info', f"Successfully parsed article: {markdown_title}")
            return markdown_title
        except Exception as e:
            self.log('error', f"Error parsing article {target_link}: {str(e)}")
            raise

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

if __name__ == "__main__":

    url = 'https://mp.weixin.qq.com/s/7XcdAvI6rROyzrGgM_6K2Q'

    # hexo_uploader=True 表示在公式前后加上 {% raw %} {% endraw %}，以便 hexo 正确解析
    parser = WeixinParser()
    parser.judge_type(url)
