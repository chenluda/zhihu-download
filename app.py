import io
import os
import shutil
import logging
from datetime import datetime
from flask import Flask, request, render_template, send_file, jsonify
from main_zhihu import ZhihuParser
from main_csdn import CsdnParser
from main_weixin import WeixinParser
import json
import zipfile

# 设置日志
if not os.path.exists('./logs'):
    os.makedirs('./logs')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='./logs/app.log',
    filemode='a'
)
logger = logging.getLogger('web_app')

app = Flask(__name__)


def create_zip_from_directory(directory, zip_path):
    """从给定目录创建ZIP文件"""
    supported_extensions = ['.md', '.jpg', '.png', '.gif', '.mp4', '.txt']
    log_files = ['zhihu_failed_articles.txt', 'zhihu_download.log', 
                'weixin_download.log', 'csdn_download.log',
                'csdn_failed_articles.txt']
    try:
        with zipfile.ZipFile(zip_path, "w") as zf:
            for root, _, files in os.walk(directory):
                for file in files:
                    if any(file.endswith(ext) for ext in supported_extensions) or file in log_files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, directory)
                        zf.write(file_path, arcname)
        return True
    except Exception as e:
        logger.error(f"Error creating zip file: {str(e)}")
        return False


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        cookies = request.form["cookies"]
        url = request.form["url"]
        website = request.form["website"].lower()

        parser_map = {
            "csdn": (CsdnParser(), "csdn"),
            "zhihu": (ZhihuParser(cookies), "zhihu"),
            "weixin": (WeixinParser(), "weixin")
        }

        try:
            parser, tmpdir = parser_map[website]
        except KeyError:
            logger.warning(f"Unsupported website: {website}")
            return "Unsupported website", 400

        try:
            os.makedirs(tmpdir, exist_ok=True)
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            
            try:
                markdown_title = parser.judge_type(url)
                logger.info(f"Successfully processed {url}, title: {markdown_title}")
            except Exception as e:
                logger.error(f"Error processing {website} URL {url}: {str(e)}")
                markdown_title = f"partial_download_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                with open(f"{markdown_title}_error.txt", "w", encoding="utf-8") as f:
                    f.write(f"Error processing URL: {url}\n")
                    f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Error: {str(e)}\n")
            
            os.chdir(old_cwd)

            zip_path = f"{markdown_title}.zip"
            
            if create_zip_from_directory(tmpdir, zip_path):
                with open(zip_path, "rb") as f:
                    zip_data = io.BytesIO(f.read())

                cleanup_files([zip_path, tmpdir])

                return send_file(zip_data, download_name=f"{markdown_title}.zip", as_attachment=True)
            else:
                return "Failed to create zip file", 500
                
        except Exception as e:
            os.chdir(old_cwd)
            logger.error(f"Error in web request for {website} URL: {e}")
            return "An error occurred while processing your request.", 500

    return render_template("index.html")

@app.route("/get-cookies")
def get_cookies():
    return render_template("howToGetCookies.html")


@app.route("/api/download", methods=["POST"])
def api_download():
    """API接口，用于处理下载请求并返回JSON格式的结果"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    cookies = data.get("cookies")
    url = data.get("url")
    website = data.get("website", "").lower()

    if not all([url, website]):
        return jsonify({"error": "Missing required parameters"}), 400

    if website == "zhihu" and not all([url, cookies, website]):
        return jsonify({"error": "Missing required parameters"}), 400
    
    parser_map = {
        "csdn": (CsdnParser(), "csdn"),
        "zhihu": (ZhihuParser(cookies), "zhihu"),
        "weixin": (WeixinParser(), "weixin")
    }

    try:
        parser, tmpdir = parser_map[website]
    except KeyError:
        return jsonify({"error": "Unsupported website"}), 400

    try:
        os.makedirs(tmpdir, exist_ok=True)
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        
        try:
            markdown_title = parser.judge_type(url)
            logger.info(f"API: Successfully processed {url}, title: {markdown_title}")
        except Exception as e:
            logger.error(f"API: Error processing {website} URL {url}: {str(e)}")
            markdown_title = f"partial_download_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(f"{markdown_title}_error.txt", "w", encoding="utf-8") as f:
                f.write(f"Error processing URL: {url}\n")
                f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Error: {str(e)}\n")
        
        os.chdir(old_cwd)

        zip_path = f"{markdown_title}.zip"
        
        if create_zip_from_directory(tmpdir, zip_path):
            with open(zip_path, "rb") as f:
                zip_data = io.BytesIO(f.read())

            cleanup_files([zip_path, tmpdir])

            filename = f"{markdown_title}.zip"
            return send_file(zip_data, download_name=filename, as_attachment=True)
        else:
            return jsonify({"error": "Failed to create zip file"}), 500
            
    except Exception as e:
        os.chdir(old_cwd)
        logger.error(f"API: Error in web request for {website} URL: {e}")
        return jsonify({"error": f"An error occurred while processing your request: {str(e)}"}), 500


def cleanup_files(paths):
    """清理指定路径下的文件和目录"""
    for path in paths:
        if os.path.exists(path):
            try:
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
            except OSError as e:
                app.logger.error(f"Failed to remove {path}: {e}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False)
