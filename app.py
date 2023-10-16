from flask import Flask, render_template, request, send_file
import io
import os
import shutil
import zipfile
from main import *

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form["url"]
        tmpdir = "zhihu"
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir)
        os.makedirs(tmpdir, exist_ok=True)

        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        markdown_title = judge_zhihu_type(url)
        os.chdir(old_cwd)

        zip_path = "zhihu.zip"

        if os.path.exists(zip_path):
            os.remove(zip_path)

        with zipfile.ZipFile(zip_path, "w") as zf:
            for root, _, files in os.walk(tmpdir):
                for file in files:
                    if file.endswith(".md") or file.endswith(".jpg"):
                        zf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), tmpdir))

        # 使用 io.BytesIO 将文件读取到内存中
        with open(zip_path, "rb") as f:
            zip_data = io.BytesIO(f.read())

        # 删除本地创建的 ZIP 文件和目录
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir)

        # 使用 send_file 发送内存中的 ZIP 文件
        return send_file(zip_data, from flask import Flask, render_template, request, send_file
import io
import os
import shutil
import zipfile
from main import *

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form["url"]
        tmpdir = "zhihu"
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir)
        os.makedirs(tmpdir, exist_ok=True)

        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        markdown_title = judge_zhihu_type(url)
        os.chdir(old_cwd)

        zip_path = "zhihu.zip"

        if os.path.exists(zip_path):
            os.remove(zip_path)

        with zipfile.ZipFile(zip_path, "w") as zf:
            for root, _, files in os.walk(tmpdir):
                for file in files:
                    if file.endswith(".md") or file.endswith(".jpg"):
                        zf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), tmpdir))

        # 使用 io.BytesIO 将文件读取到内存中
        with open(zip_path, "rb") as f:
            zip_data = io.BytesIO(f.read())

        # 删除本地创建的 ZIP 文件和目录
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir)

        # 使用 send_file 发送内存中的 ZIP 文件
        return send_file(zip_data, attachment_filename = f"{markdown_title}.zip", as_attachment=True)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=False)
