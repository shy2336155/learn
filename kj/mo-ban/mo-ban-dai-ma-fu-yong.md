# 模板代码复用

在模板中，可能会遇到以下情况：
- 多个模板具有完全相同的顶部和底部内容
- 多个模板中具有相同的模板代码内容，但是内容中部分值不一样
- 多个模板中具有完全相同的 html 代码块内容

像遇到这种情况，可以使用 JinJa2 模板中的 宏、继承、包含来进行实现