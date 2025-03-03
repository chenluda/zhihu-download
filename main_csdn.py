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
from utils.util import insert_new_line, get_article_date, download_image, download_video, get_valid_filename, get_article_date_csdn


class CsdnParser:
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
        self.logger = logging.getLogger('csdn_parser')
        
        if self.keep_logs:
            self.logger.setLevel(logging.INFO)
            if not self.logger.handlers and not os.path.exists('./logs'):
                os.makedirs('./logs', exist_ok=True)
            
            if not self.logger.handlers:
                handler = logging.FileHandler(
                    './logs/csdn_download.log', encoding='utf-8')
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
            if target_link.find("category") != -1:
                # 如果是专栏
                title = self.parse_column(target_link)
            else:
                # 如果是单篇文章
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

            # 处理回答中的图片
            for img in content_element.find_all("img"):
                try:
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
                except Exception as e:
                    self.log('warning', f"Error downloading image {img.get('src', 'unknown')}: {str(e)}")
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

            title_element = self.soup.select_one("h1.title-article")
            content_element = self.soup.select_one("div#content_views")

            if not title_element or not content_element:
                self.log('warning', "Could not find title or content elements")
                if not title_element:
                    self.log('warning', "Missing title element")
                if not content_element:
                    self.log('warning', "Missing content element")

            author_element = self.soup.select_one('div.bar-content')
            if author_element and author_element.find_all("a"):
                author = author_element.find_all("a")[0].text.strip()
                date = get_article_date_csdn(author_element)
            else:
                author = "未知作者"
                date = None
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

    def parse_column(self, target_link):
        """
        解析知乎专栏并保存为 Markdown 格式文件
        """
        try:
            self.check_connect_error(target_link)

            # 将所有文章放在一个以专栏标题命名的文件夹中
            title = self.soup.text.split('-')[0].split('_')[0].strip()
            
            try:
                total_articles = int(self.soup.text.split(
                    '文章数：')[-1].split('文章阅读量')[0].strip())  # 总文章数
            except (ValueError, IndexError):
                # 如果无法解析总文章数，使用-1表示未知
                total_articles = -1
                self.log('warning', "Could not determine total article count, using undefined count")
                
            folder_name = get_valid_filename(title)
            os.makedirs(folder_name, exist_ok=True)
            os.chdir(folder_name)

            processed_filename = "csdn_processed_articles.txt"
            processed_articles = self.load_processed_articles(processed_filename)
            failed_articles_filename = "csdn_failed_articles.txt"

            # 读取失败的文章列表，用于记录
            failed_articles = set()
            if os.path.exists(failed_articles_filename):
                with open(failed_articles_filename, 'r', encoding='utf-8') as file:
                    failed_articles = set(file.read().splitlines())

            offset = 0
            success_count = 0
            failure_count = 0

            # 计算已处理的文章数
            already_processed = len(processed_articles)

            # 初始化进度条，从已处理的文章数开始
            if total_articles > 0:
                progress_bar = tqdm(
                    total=total_articles, initial=already_processed, desc="解析文章")
            else:
                # 如果无法确定总数，就使用一个无限进度条
                progress_bar = tqdm(desc="解析文章")

            ul_element = self.soup.find('ul', class_='column_article_list')
            if not ul_element:
                self.log('error', "Could not find article list element")
                raise ValueError("Article list not found on page")
                
            for li in ul_element.find_all('li'):
                try:
                    article_link = li.find('a')['href']
                    article_id = article_link.split('/')[-1]
                    
                    # 如果已经处理过，跳过
                    if article_id in processed_articles:
                        continue

                    # 如果之前失败过，再试一次
                    retry_failed = article_id in failed_articles
                    
                    try:
                        self.parse_article(article_link)
                        # 成功处理，记录并更新进度
                        self.save_processed_article(processed_filename, article_id)
                        if retry_failed:
                            failed_articles.remove(article_id)
                            # 更新失败文件
                            with open(failed_articles_filename, 'w', encoding='utf-8') as file:
                                file.write('\n'.join(failed_articles))
                        success_count += 1
                        progress_bar.update(1)  # 更新进度条
                    except Exception as e:
                        failure_count += 1
                        # 记录失败的文章
                        failed_articles.add(article_id)
                        with open(failed_articles_filename, 'a', encoding='utf-8') as file:
                            file.write(f"{article_id}\n")
                        self.log('error', f"Error processing article {article_id}: {str(e)}")
                        # 继续处理下一篇文章
                except Exception as e:
                    self.log('warning', f"Error processing list item: {str(e)}")
                    # 继续处理下一个列表项

            progress_bar.close()  # 完成后关闭进度条

            # 如果失败文件为空，则删除
            if len(failed_articles) == 0 and os.path.exists(failed_articles_filename):
                os.remove(failed_articles_filename)

            self.log('info', f"Column processing complete. Success: {success_count}, Failed: {failure_count}")
            
            # 只有在全部成功的情况下删除已处理文件
            if failure_count == 0 and os.path.exists(processed_filename):
                os.remove(processed_filename)

            return folder_name
        except Exception as e:
            self.log('error', f"Error parsing column {target_link}: {str(e)}")
            # 在这种情况下，返回当前文件夹名，以便打包已下载的内容
            return os.path.basename(os.getcwd())


if __name__ == "__main__":

    # url = 'https://blog.csdn.net/weixin_45490023/article/details/128380766'
    url = 'https://blog.csdn.net/weixin_45490023/category_12351077.html'

    # hexo_uploader=True 表示在公式前后加上 {% raw %} {% endraw %}，以便 hexo 正确解析
    parser = CsdnParser()
    parser.judge_type(url)