# 将知乎专栏文章转换为 Markdown 文件保存到本地

![image](https://github.com/chenluda/zhihu-download/assets/45784833/60e0d85b-8f48-493f-ac1f-e87e2f0738a2)

* 2023-05-29 14:20:21 Update main.py：修改代码，以适应最新的知乎 HTML 结构；
* 2023-06-12 19:59:31 Update main.py：修改代码，修复数学公式没有转换成 Markdown 格式的 bug；将文件名改为标题的后 20 个字符，以防重复；
* 2023-06-22 11:07:51 Update main.py：修改代码，为数学公式添加转义符号以免 hexo 无法识别（可选）；
* 2023-08-19 10:30:00 Update main.py：修改代码，修复数学公式出现三 $ 的 bug；获取卡片链接；
* 2023-10-27 15:21:15 Update main.py：修改代码，修复 bug - 1）main.py 的 46 行重复粘贴；2) 有些文章图片为 png 格式，无法下载；3）在文件名称前加该文章的编辑时间；4）增加专栏文章下载的断点续传；5）对卡片链接进行优化，删除知乎安全链接前缀。感谢 [Aswatthafei](https://github.com/Aswatthafei) 的提醒！



---

## 运行环境

```
flask 1.1.2
flask-cors 4.0.0
python 3.9
```

flask 2.2 以上版本需要将 app.py 中第 46 行，

```
return send_file(zip_data, attachment_filename = markdown_title + ".zip", as_attachment=True)
```

改为：

```
return send_file(zip_data, download_name = markdown_title + ".zip", as_attachment=True)
```

---

运行代码
```
python app.py
```


