<div align="center">
  <h2>知乎专栏文章 Markdown 转换器</h2>
  <p>一键将知乎专栏文章转换并保存为 Markdown 文件</p>
  <a href="#">
    <img alt="Python 3.9" src="https://img.shields.io/badge/python-3.9-blue.svg" />
  </a>
  <a href="#">
    <img alt="Flask 2.3.3" src="https://img.shields.io/badge/flask-2.3.3-blue.svg" />
  </a>
  <a href="#">
    <img alt="Status" src="https://img.shields.io/badge/Status-Updating-green" />
  </a>
</div>

![image](https://github.com/chenluda/zhihu-download/assets/45784833/5a5c27fb-4419-43fd-9ab9-69bdbe6667fe)

## 特点

⭐ **支持最新 HTML 结构**：持续更新以适应知乎平台的变化。

⭐ **断点续传功能**：支持大体量专栏文章下载的断点续传，提高使用便利性。

⭐ **完善的数学公式支持**：特别优化了数学公式的提取和转换，保证了复杂内容的准确性和完整性。

⭐ **图片下载与处理**：处理并优化文章中的图片链接，确保转换后的 Markdown 文件包含原文的所有视觉元素。

## 运行环境

```
flask 2.3.3
flask-cors 4.0.0
python 3.9
```
运行代码
```
python app.py
```
> **Note**
>
> flask 2.2 以下版本需要将 app.py 中第 46 行，
> ``` python
> return send_file(zip_data, download_name = markdown_title + ".zip", as_attachment=True)
> ```
> 改为：
> ``` python
> return send_file(zip_data, attachment_filename = markdown_title + ".zip", as_attachment=True)
> ```

> **Note**
>
> 因为我们遇到过文件名太长，导致图片不能显示的情况，所以我们刻意限制了文件名的长度，但多数情况下是可以使用全名的，如果需要使用全名，请将 main.py 中的第 87 行注释掉，
> ``` python
> markdown_title = get_valid_filename(title[-20:-1])
> ```
> 将第 89 行的注释打开
> ``` python
> markdown_title = get_valid_filename(title)
> ```

## 更新日志

* 2023-05-29：适应知乎最新 HTML 结构。
* 2023-06-12：修复数学公式 Markdown 转换 bug。
* 2023-06-22：为数学公式添加转义符号，增强兼容性。
* 2023-08-19：修复公式和卡片链接相关的多项 bug。
* 2023-10-27：优化代码，增加断点续传功能，改进图片处理和链接优化。（感谢 [Aswatthafei](https://github.com/Aswatthafei) 的提醒！）
