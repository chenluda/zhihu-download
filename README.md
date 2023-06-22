# 将知乎专栏文章转换为 Markdown 文件保存到本地

![image](https://github.com/chenluda/zhihu-download/assets/45784833/60e0d85b-8f48-493f-ac1f-e87e2f0738a2)

* 2023-05-29 14:20:21 Update main.py：修改代码，以适应最新的知乎 HTML 结构；
* 2023-06-12 19:59:31 Update main.py：修改代码，修复数学公式没有转换成 Markdown 格式的 bug；将文件名改为标题的后 20 个字符，以防重复；
* 2023-06-22 11:07:51 Update main.py：修改代码，为数学公式添加转义符号以免 hexo 无法识别（可选）。

---

最近想构建一个本地知识库。

需要从知乎下载文章、专栏、回答，并以 Markdown 格式保存到本地。

自己写了个脚本，

可以判断给定 url 的类型，是文章、专栏还是回答，三种类型的处理方式不同；
然后将图片保存至本地，并将转换的 Markdown 中图片 url 更换为本地路径，使图片可以在本地显示。

---

运行代码
```
python app.py
```

