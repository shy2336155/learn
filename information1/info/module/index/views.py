from info.models import User, News, Category
from info.utitls.response_code import RET
from . import index_bp
from flask import session, current_app, render_template, jsonify, request, g
from info import constants
from info import redis_store
import logging
from info.utitls.common import user_login_data


# 127.0.0.1:5000/news_list
@index_bp.route('/news_list')
def news_list():
    """获取新闻列表数据后端接口"""
    """
    1.获取参数
        1.1 cid:分类id（表明要获取那个分类对应的新闻数据）
            page:当前页码（默认值：1）， 
            per_page:每一页多少条新闻（默认值：10）
    2.参数校验
        2.1 cid是否为空
        2.2 数据格式校验是否能转换成int类型
    3.逻辑处理
        3.1 调用分页方法paginate查询新闻列表数据
        3.2 将新闻对象列表转换成新闻字典列表 
    4.返回值
    """
    # 1.1 cid:分类id（表明要获取那个分类对应的新闻数据） page:当前页码（默认值：1）， per_page:每一页多少条新闻（默认值：10）
    param_dict = request.args
    cid = param_dict.get("cid")
    page = param_dict.get("page", 1)
    per_page = param_dict.get("per_page", 10)
    # 2.1 cid是否为空
    if not cid:
        current_app.logger.error("参数不足")
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    # 2.2 数据格式校验是否能转换成int类型
    try:
        cid = int(cid)
        page = int(page)
        per_page = int(per_page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数格式错误")

    # 3.1 调用分页方法paginate查询新闻列表数据
    """
    paginate() 参数1：当前第几页， 参数2：当前页码多少条数据 参数3:不需要错误输出
    
    # 2 3 4 ...其他分类
    if cid != 1:
        paginate = News.query.filter(News.category_id == cid).order_by(News.create_time.desc()) \
            .paginate(page, per_page, False)
    else:
        # 分类为最新的数据只需要根据时间降序排
        paginate = News.query.filter().order_by(News.create_time.desc()) \
            .paginate(page, per_page, False)
    """
    # 查询条件列表
    # 默认查询条件是审核通过的新闻
    filter_list = [News.status == 0]
    # 不是最新分类
    if cid != 1:
        # 底层sqlalchemy会重新 == 符号返回一个`查询条件`而不是`Bool值`
        # 将查询条件添加到列表
        filter_list.append(News.category_id == cid)

    # *filter_list 解包将里面内容一个拿出来
    try:
        paginate = News.query.filter(*filter_list).order_by(News.create_time.desc()) \
            .paginate(page, per_page, False)

        # 获取当前页码所有新闻对象列表数据
        news_list = paginate.items
        # 获取当前页码
        current_page = paginate.page
        # 获取总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询新闻对象列表异常")

    # 3.2 将新闻对象列表转换成新闻字典列表
    news_dict_list = []
    for news in news_list if news_list else []:
        # 新闻对象转换成字典对象并添加到新闻字典列表
        news_dict_list.append(news.to_dict())

    # 3.3 构建返回数据
    data = {
        "newsList": news_dict_list,
        "current_page": current_page,
        "total_page": total_page
    }

    # 4.返回值
    return jsonify(errno=RET.OK, errmsg="新闻列表数据查询成功", data=data)



# 2.使用蓝图
@index_bp.route('/')
@user_login_data
def index():

    # ----------------1. 查询用户登录信息，进行展示------------------------
    user = g.user
    # 将用户对象数据转换成字典数据，借助模板展示
    # if user:
    #     user_dict = user.to_dict()

    # ----------------2. 查询新闻点击排行数据------------------------

    try:
        news_rank_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询新闻数据异常")
    """
       新闻对象列表 转换成 新闻字典列表
       news_rank_list ==> [news_obj, news_obj1, ....]
       news_dict_list ==> [news_dict,news_dict1,.....]
       
        if news_rank_list:
            for news_obj in news_rank_list:
                # 新闻对象转换成字典
                news_dict = news_obj.to_dict()
                news_dict_list.append(news_dict)
    """
    news_dict_list = []
    for news_obj in news_rank_list if news_rank_list else []:
        # 新闻对象转换成字典
        news_dict = news_obj.to_dict()
        news_dict_list.append(news_dict)

    # ----------------3. 查询新闻分类数据 ------------------------
    try:
         categories = Category.query.all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询分类数据异常")

    # 分类对象列表转换成字典列表
    categories_dict_list = []
    for category in categories if categories else []:
        # 分类对象转出成字典
        category_dict = category.to_dict()
        categories_dict_list.append(category_dict)

    # 首页数据字典
    data = {
        "user_info": user.to_dict() if user else None,
        "news_rank_list": news_dict_list,
        "categories": categories_dict_list
    }

    return render_template("news/index.html", data=data)


@index_bp.route("/favicon.ico")
def get_favicon():
    """获取网站图标"""

    """
    Function used internally to send static files from the static
        folder to the browser
    内部用来发送静态文件到浏览器的方法
    """
    return current_app.send_static_file("news/favicon.ico")


















