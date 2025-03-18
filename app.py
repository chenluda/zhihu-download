import io
import os
import shutil
import logging
from datetime import datetime
from flask import Flask, request, render_template, send_file, jsonify
from main_zhihu import ZhihuParser
from main_csdn import CsdnParser
from main_weixin import WeixinParser
from main_juejin import JuejinParser
import json
import zipfile

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
    log_files = ['zhihu_download.log', 'weixin_download.log', 'csdn_download.log',]

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
        keep_logs = request.form.get("keep_logs") == "on"

        parser_map = {
            "csdn": (CsdnParser(keep_logs=keep_logs), "csdn"),
            "zhihu": (ZhihuParser(cookies, keep_logs=keep_logs), "zhihu"),
            "weixin": (WeixinParser(keep_logs=keep_logs), "weixin"),
            "juejin": (JuejinParser(keep_logs=keep_logs), "juejin")
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


@app.route("/api/logs", methods=["GET"])
def get_logs():
    """API endpoint to retrieve logs"""
    log_type = request.args.get('type', 'app')

    log_files = {
        'zhihu': './logs/zhihu_download.log',
        'csdn': './logs/csdn_download.log',
        'weixin': './logs/weixin_download.log',
        'juejin': './logs/juejin_download.log',
    }

    if log_type not in log_files:
        return jsonify({"error": "Invalid log type"}), 400

    log_path = log_files[log_type]
    if not os.path.exists(log_path):
        return jsonify({"logs": f"Log file {log_path} not found"}), 404

    try:
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']

        for encoding in encodings:
            try:
                with open(log_path, 'r', encoding=encoding, errors='replace') as f:
                    lines = f.readlines()
                    return jsonify({"logs": ''.join(lines)})
            except UnicodeDecodeError:
                continue

        with open(log_path, 'rb') as f:
            binary_content = f.read()
            text_content = binary_content.decode('utf-8', errors='replace')
            return jsonify({"logs": text_content})

    except Exception as e:
        logger.error(f"Error reading log file {log_path}: {str(e)}")
        return jsonify({"error": f"Failed to read log file: {str(e)}"}), 500


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
