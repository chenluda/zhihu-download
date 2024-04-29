import io
import os
import shutil
import zipfile
from flask import Flask, request, render_template, send_file, after_this_request
from main import *

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        cookies = request.form["cookies"]
        # cookies = 'your_zhihu_cookies'
        url = request.form["url"]
        tmpdir = "zhihu"
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir)
        os.makedirs(tmpdir, exist_ok=True)

        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        markdown_title = judge_zhihu_type(url, cookies, None)
        os.chdir(old_cwd)

        zip_path = "zhihu.zip"

        if os.path.exists(zip_path):
            os.remove(zip_path)

        # 定义支持的文件扩展名列表
        supported_extensions = [".md", ".jpg", ".png", ".gif"]

        with zipfile.ZipFile(zip_path, "w") as zf:
            for root, _, files in os.walk(tmpdir):
                for file in files:
                    if any(file.endswith(ext) for ext in supported_extensions):
                        zf.write(os.path.join(root, file), os.path.relpath(
                            os.path.join(root, file), tmpdir))

        # 使用 io.BytesIO 将文件读取到内存中
        with open(zip_path, "rb") as f:
            zip_data = io.BytesIO(f.read())

        # 删除本地创建的 ZIP 文件和目录
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(tmpdir):
            try:
                shutil.rmtree(tmpdir)
            except:
                print(f"Unable to delete temporary directory: {tmpdir}")

        # 使用 send_file 发送内存中的 ZIP 文件
        return send_file(zip_data, download_name=f"{markdown_title}.zip", as_attachment=True)

    return render_template("index.html")


@app.route("/get-cookies")
def get_cookies():
    return render_template("howToGetCookies.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False)
