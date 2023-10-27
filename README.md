<div align="center">
  <h2>知乎专栏文章 Markdown 转换器</h2>
  <p>一键将知乎专栏文章转换并保存为 Markdown 文件</p>
  <a href="#">
    <img alt="Status" src="https://img.shields.io/badge/Status-Updating-green" />
  </a>
</div>

![image](https://github.com/chenluda/zhihu-download/assets/45784833/5a5c27fb-4419-43fd-9ab9-69bdbe6667fe)

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

## 更新日志

* 2023-05-29：适应知乎最新 HTML 结构。
* 2023-06-12：修复数学公式 Markdown 转换 bug。
* 2023-06-22：为数学公式添加转义符号，增强兼容性。
* 2023-08-19：修复公式和卡片链接相关的多项 bug。
* 2023-10-27：优化代码，增加断点续传功能，改进图片处理和链接优化。（感谢 [Aswatthafei](https://github.com/Aswatthafei) 的提醒！）
