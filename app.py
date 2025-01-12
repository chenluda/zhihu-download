import io
import os
import shutil
from flask import Flask, request, render_template, send_file
from main_zhihu import ZhihuParser
from main_csdn import CsdnParser
import zipfile

app = Flask(__name__)

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

            return send_file(zip_data, download_name=f"{markdown_title}.zip", as_attachment=True)
        except Exception as e:
            app.logger.error(f"Error processing {website} URL: {e}")
            return "An error occurred while processing your request.", 500

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