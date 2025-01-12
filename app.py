'''
Author: chenluda01@outlook.com
Date: 2023-10-29 20:34:35
LastEditors: chenluda01@outlook.com
LastEditTime: 2025-01-12 19:02:57
Description: 
FilePath: \zhihu-download\app.py
'''
import io
import os
import shutil
from datetime import datetime
from flask import Flask, request, render_template, send_file
from main_zhihu import ZhihuParser
from main_csdn import CsdnParser
from redis import Redis
import zipfile

app = Flask(__name__)
redis_client = Redis(host='redis', port=6379, decode_responses=True)

def record_visit():
    """记录访问者信息到Redis"""
    visitor_ip = request.remote_addr
    today = datetime.now().strftime('%Y-%m-%d')
    
    total_key = 'visitor_total'
    daily_key = f'visitor_{today}'
    if not redis_client.sismember(daily_key, visitor_ip):
        redis_client.sadd(daily_key, visitor_ip)
        redis_client.expire(daily_key, 86400)  # 设置一天过期时间
        redis_client.incr(total_key)

def get_statistics():
    """获取统计信息"""
    today = datetime.now().strftime('%Y-%m-%d')
    total_visits = redis_client.get('visitor_total') or 0
    daily_visits = redis_client.scard(f'visitor_{today}') or 0
    total_downloads = redis_client.get('download_total') or 0
    return int(total_visits), int(daily_visits), int(total_downloads)

def create_zip_from_directory(directory, zip_path):
    """从给定目录创建ZIP文件"""
    supported_extensions = ['.md', '.jpg', '.png', '.gif']
    with zipfile.ZipFile(zip_path, "w") as zf:
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in supported_extensions):
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, directory)
                    zf.write(file_path, arcname)

@app.route("/", methods=["GET", "POST"])
def index():
    # record_visit()
    # total_visits, daily_visits, total_downloads = get_statistics()

    if request.method == "POST":
        cookies = request.form["cookies"]
        url = request.form["url"]
        website = request.form["website"].lower()  # 确保大小写不敏感
        
        parser_map = {
            "csdn": (CsdnParser(), "csdn"),
            "zhihu": (ZhihuParser(cookies), "zhihu")
        }
        
        try:
            parser, tmpdir = parser_map[website]
        except KeyError:
            return "Unsupported website", 400

        try:
            os.makedirs(tmpdir, exist_ok=True)
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            markdown_title = parser.judge_type(url) if website == "csdn" else parser.judge_zhihu_type(url)
            os.chdir(old_cwd)

            zip_path = f"{markdown_title}.zip"
            create_zip_from_directory(tmpdir, zip_path)

            with open(zip_path, "rb") as f:
                zip_data = io.BytesIO(f.read())

            cleanup_files([zip_path, tmpdir])
            # redis_client.incr('download_total')

            return send_file(zip_data, download_name=f"{markdown_title}.zip", as_attachment=True)
        except Exception as e:
            app.logger.error(f"Error processing {website} URL: {e}")
            return "An error occurred while processing your request.", 500

    # return render_template("index.html", total_visits=total_visits, daily_visits=daily_visits, total_downloads=total_downloads)
    return render_template("index.html")

@app.route("/get-cookies")
def get_cookies():
    return render_template("howToGetCookies.html")

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