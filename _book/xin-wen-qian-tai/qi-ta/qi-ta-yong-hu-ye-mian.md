# 其他用户界面

## 需求

- 从新闻详情页面的作者信息和我的关注的用户列表可以进入其他用户信息界面
- 进入界面之后展示用户的个人信息以及其发布的新闻列表信息

## 实现准备

- 将 `static/news/other.html` 拖到 `templates/news` 目录下
- 继承基类模板，抽取相关代码
    - 注意此处 main.css 导入顺序


## 代码实现

- 在 `modules/profile/views.py` 中添加视图函数，渲染该模板页面

```python
@profile_blu.route('/other_info')
@user_login_data
def other_info():
    """查看其他用户信息"""
    user = g.user

    # 获取其他用户id
    user_id = request.args.get("id")
    if not user_id:
        abort(404)
    # 查询用户模型
    other = None
    try:
        other = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
    if not other:
        abort(404)

    # 判断当前登录用户是否关注过该用户
    is_followed = False
    if g.user:
        if other.followers.filter(User.id == user.id).count() > 0:
            is_followed = True

    # 组织数据，并返回
    data = {
        "user_info": user.to_dict(),
        "other_info": other.to_dict(),
        "is_followed": is_followed
    }
    return render_template('news/other.html', data=data)
```

- `news/other.html` 模板页面数据填充

```html
<div class="user_center_pic">
    <img src="{% if data.other_info.avatar_url %}
    {{ data.other_info.avatar_url }}
    {% else %}
    ../../static/news/images/user_pic.png
    {% endif %}" alt="用户图片">
</div>
<div class="user_center_name">{{ data.other_info.nick_name }}</div>

<ul class="other_detail">
    <li>性 别：{% if data.other_info.gender == "MAN" %}男
    {% else %}女
    {% endif %}</li>
    <li>签 名：{% if data.other_info.signature %}
        {{ data.other_info.signature }}
    {% else %}
        这个人很懒，什么都没留下
    {% endif %}</li>
</ul>

<div class="focus_other">
    <a href="javascript:;" class="focus block-center" data-userid="{{ data.other_info.id }}" style="display: {% if data.is_followed %}none
    {% else %}block
    {% endif %}">关注</a><br>
    <a href="javascript:;" class="focused block-center" data-userid="{{ data.other_info.id }}" style="display: {% if data.is_followed %}block
    {% else %}none
    {% endif %}"><span class="out">已关注</span><span class="over">取消关注</span></a>
</div>
```

- 添加视图函数用于提供其他用户新闻列表

```python
@profile_blu.route('/other_news_list')
def other_news_list():
    # 获取页数
    p = request.args.get("p", 1)
    user_id = request.args.get("user_id")
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if not all([p, user_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")

    if not user:
        return jsonify(errno=RET.NODATA, errmsg="用户不存在")

    try:
        paginate = News.query.filter(News.user_id == user.id).paginate(p, constants.OTHER_NEWS_PAGE_MAX_COUNT, False)
        # 获取当前页数据
        news_li = paginate.items
        # 获取当前页
        current_page = paginate.page
        # 获取总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")

    news_dict_li = []

    for news_item in news_li:
        news_dict_li.append(news_item.to_review_dict())
    data = {"news_list": news_dict_li, "total_page": total_page, "current_page": current_page}
    return jsonify(errno=RET.OK, errmsg="OK", data=data)
```

- 在 `news/other.js` 中实现加载数据的方法

```js
function getNewsList(page) {
    var query = decodeQuery()
    var params = {
        "p": page,
        "user_id": query["id"]
    }
    $.get("/user/other_news_list", params, function (resp) {
        if (resp.errno == "0") {
            // 先清空原有的数据
            $(".article_list").html("");
            // 拼接数据
            for (var i = 0; i<resp.data.news_list.length; i++) {
                var news = resp.data.news_list[i];
                var html = '<li><a href="/news/'+ news.id +'" target="_blank">' + news.title + '</a><span>' + news.create_time + '</span></li>'
                // 添加数据
                $(".article_list").append(html)
            }
            // 设置页数和总页数
            $("#pagination").pagination("setPage", resp.data.current_page, resp.data.total_page);
        }else {
            alert(resp.errmsg)
        }
    })
}
```

> 运行测试

- 在【新闻详情页】以及【我的关注】添加跳转链接 

```html
{% block authorBlock %}
    {% if data.news.author %}
        <div class="author_card">
            <a href="/user/other_info?id={{ data.news.author.id }}" target="_blank" class="author_pic"><img src="{% if data.news.author.avatar_url %}
            {{ data.news.author.avatar_url }}
            {% else %}
            ../../static/news/images/user_pic.png
            {% endif %}" alt="author_pic"></a>
            <a href="/user/other_info?id={{ data.news.author.id }}" target="_blank" class="author_name">{{ data.news.author.nick_name }}</a>
            ...
        </div>
    {% endif %}
{% endblock %}
```
