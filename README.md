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
  <a href="http://8.130.108.230:5000/" target="_blank">
    <img alt="web" src="https://img.shields.io/badge/演示网站-Web-red" />
  </a>
</div>

<div align="center">
  <img src="https://github.com/chenluda/zhihu-download/assets/45784833/13e59d0c-caf0-47d7-8edc-5dbef49b70cb" alt="Zhihu Article">
</div>

## 特点

⭐ **支持最新 HTML 结构**：持续更新以适应知乎平台的变化。

![gif](https://github.com/chenluda/zhihu-download/assets/45784833/849366a0-19ac-43ff-8f13-54aff24c7df3)

⭐ **断点续传功能**：支持大体量专栏文章下载的断点续传，提高使用便利性。

![gif](https://github.com/chenluda/zhihu-download/assets/45784833/9b4fd579-a492-4052-b5d8-0eb887af3a27)

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
> Internet Download Manager (IDM) 会自动拦截下载链接并进行处理，导致两次请求。  
> 也不是什么大问题，有强迫症的朋友可以将网站加入 IDM 的 '下列地址不要自动开始下载'。  
> 1. 打开 IDM 界面，菜单栏 '下载' -> '选项' -> '文件类型'；
> 2. 找到 '下列地址不要自动开始下载：' 文字下方的 '编辑列表...' 按钮；
> 3. 对于本地部署，直接将 'http://127.0.0.1:5000/' 加入。线上部署，将对应网址加入。

> **Note**
>
> 因为我们遇到过文件名太长，导致图片不能显示的情况，所以我们刻意限制了文件名的长度，但多数情况下是可以使用全名的，如果需要使用全名，请将 main.py 中的第 87 行注释掉，
> ``` python
> markdown_title = get_valid_filename(title[-20:-1])
> ```
> 将第 89 行的注释打开：
> ``` python
> markdown_title = get_valid_filename(title)
> ```

## 更新日志

* 2023-05-29：适应知乎最新 HTML 结构。
* 2023-06-12：修复数学公式 Markdown 转换 bug。
* 2023-06-22：为数学公式添加转义符号，增强兼容性。
* 2023-08-19：修复公式和卡片链接相关的多项 bug。
* 2023-10-27：优化代码，增加断点续传功能，改进图片处理和链接优化。（感谢 [Aswatthafei](https://github.com/Aswatthafei) 的提醒！）
* 2023-11-16：优化链接等格式。
* 2023-11-22：更改内容标题格式。
* 2023-12-27：更改内容标题格式；增加对数学公式中 `\tag{*}` 的特殊处理。（感谢 [korruz](https://github.com/korruz) 的意见！）
* 2024-03-14：增加动图支持；更改链接格式；
* 2024-04-22：增加 Cookies 以应对验证机制；

## 趋势

[![Star History Chart](https://api.star-history.com/svg?repos=chenluda/zhihu-download&type=Date)](https://star-history.com/#chenluda/zhihu-download&Date)
