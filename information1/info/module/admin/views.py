from info.models import User, News, Category
from info.utitls.response_code import RET
from . import admin_bp
from flask import render_template, request, current_app, session, redirect, url_for, abort, jsonify
import time
from datetime import datetime, timedelta
from info import constants, db
from info.utitls.pic_storage import pic_storage


@admin_bp.route('/add_category', methods=["POST"])
def add_category():
    """编辑/新增分类"""
    """
    1.获取参数
        1.1 id：分类id(非必传), name:分类名称
    2.校验参数
        2.1 非空判断
    3.逻辑处理
        3.0 id存在表示需要编辑分类，根据id查询出对应分类对象，再编辑分类对象的名称
        3.1 id不存在表示新增分类，创建分类对象，给其name属性赋值即可
        3.3 保存回数据库
    4.返回值
    """
    # 1.1 id：分类id(非必传), name:分类名称
    id = request.json.get("id")
    name = request.json.get("name")
    # 2.1 非空判断
    if not name:
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    # 3.0 id存在表示需要编辑分类，根据id查询出对应分类对象，再编辑分类对象的名称
    if id:
        try:
           category = Category.query.get(id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询分类对象异常")

        if not category:
            return jsonify(errno=RET.NODATA, errmsg="分类不存在")
        else:
            # 分类存在，进行编辑
            category.name = name

    # 3.1 id不存在表示新增分类，创建分类对象，给其name属性赋值即可
    else:
        category = Category()
        category.name = name
        db.session.add(category)

    # 3.3 保存回数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存分类对象异常")

    # 4.返回编辑成功
    return jsonify(errno=RET.OK, errmsg="OK")


@admin_bp.route('/news_category')
def news_category():
    # 获取分类数据
    try:
        categories = Category.query.all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询分类异常")

    # 对象列表转字典列表
    # 模型列表转换字典列表
    category_dict_list = []
    for category in categories if categories else []:
        category_dict = category.to_dict()
        category_dict_list.append(category_dict)

    # 移除最新分类
    category_dict_list.pop(0)

    data = {
        "categories": category_dict_list
    }
    return render_template("admin/news_type.html", data=data)


@admin_bp.route('/news_edit_detail', methods=["POST", "GET"])
def news_edit_detail():
    """新闻编辑的详情接口"""
    if request.method == "GET":
        """
        展示新闻编辑详情页面的数据
        127.0.0.1:5000/admin/news_edit_detail?news_id=1
        """
        # 获取get请求携带的新闻id
        news_id = request.args.get("news_id")

        news = None  # type:News
        if news_id:
            try:
                news = News.query.get(news_id)
            except Exception as e:
                current_app.logger.error(e)
                return abort(404)

        # 新闻对象转字典对象
        news_dict = None
        if news:
            news_dict = news.to_dict()

        # 查询所有分类数据
        # 获取分类数据
        try:
            categories = Category.query.all()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询分类异常")

        # 对象列表转字典列表
        # 模型列表转换字典列表
        category_dict_list = []
        for category in categories if categories else []:
            category_dict = category.to_dict()

            # 默认没有选中任何一个分类
            category_dict["is_selected"] = False
            # 分类的id等于新闻对应的分类id
            # 1 = 1 True
            # 2 = 1 False
            if category.id == news.category_id:
                # 表示需要选中的新闻分类
                category_dict["is_selected"] = True

            category_dict_list.append(category_dict)

        # 移除最新分类
        category_dict_list.pop(0)
        data = {
            "news": news_dict,
            "categories": category_dict_list
        }

        return render_template("admin/news_edit_detail.html", data=data)

    # POST请求：新闻数据编辑
    """
    1.获取参数
        1.1 news_id:新闻id， title：新闻标题，category_id:新闻分类id
            digest:新闻摘要，index_image:新闻主图片（非必传），content：新闻内容
    2.校验参数
        2.1 非空判断
    3.逻辑处理
        
        3.0 如果存在主图片，需要上传到七牛云
        3.1 根据news_id查询对应新闻
        3.2 给新闻对象各个属性重新赋值
        3.3 保存回数据库
    4.返回值
    """
    # 因为前段使用ajaxSubmit所有数据是form表单提交的
    param_dict = request.form
    #  1.1 news_id:新闻id， title：新闻标题，category_id:新闻分类id
    #  digest:新闻摘要，index_image:新闻主图片（非必传），content：新闻内容
    news_id = param_dict.get("news_id")
    title = param_dict.get("title")
    category_id = param_dict.get("category_id")
    digest = param_dict.get("digest")
    content = param_dict.get("content")
    # 图片数据
    index_image = request.files.get("index_image")

    # 2.1非空判断
    if not all([news_id, title, category_id, digest, content]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    # 修改了图片，将修改的图片上传到七牛云
    # 3.1 如果存在主图片，需要上传到七牛云
    image_name = None
    if index_image:
        try:
            image_name = pic_storage(index_image.read())
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.THIRDERR, errmsg="上传到七牛云失败")

    #  3.1 根据news_id查询对应新闻
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询新闻对象异常")
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="新闻不存在")

    #  3.2 给新闻对象各个属性重新赋值
    news.title = title
    news.category_id = category_id
    news.digest = digest
    news.content = content
    # 如果上传七牛云成功后，才给图片属性赋值
    if image_name:
        news.index_image_url = constants.QINIU_DOMIN_PREFIX + image_name
    #  3.3 保存回数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存新闻对象异常")

    # 4.返回编辑成功
    return jsonify(errno=RET.OK, errmsg="编辑新闻成功")


# 127.0.0.1:5000/admin/news_edit
@admin_bp.route('/news_edit')
def news_edit():
    """新闻编辑页面展示"""

    # 1.获取要查询的页码
    p = request.args.get("p", 1)
    # 查询关键字（非必传的）
    keywords = request.args.get("keywords")
    # 2.页码校验
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    news_list = []
    current_page = 1
    total_page = 1

    # 查询条件列表 默认查询条件是：审核未通过&未审核的新闻
    filter_list = []

    if keywords:
        # 关键字是否包含于新闻标题，进行查询
        filter_list.append(News.title.contains(keywords))

    try:
        paginate = News.query.filter(*filter_list).order_by(News.create_time.desc())\
            .paginate(p, constants.ADMIN_NEWS_PAGE_MAX_COUNT, False)

        # 获取当前页码的所有数据
        news_list = paginate.items
        # 当前页码
        current_page = paginate.page
        # 总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return abort(404)

    # 对象列表转字典列表
    news_dict_list = []
    for news in news_list if news_list else []:
        news_dict_list.append(news.to_basic_dict())

    # 组织响应数据
    data = {
        "news_list": news_dict_list,
        "current_page": current_page,
        "total_page": total_page
    }

    return render_template("admin/news_edit.html", data=data)


@admin_bp.route('/news_review_detail', methods=["POST", "GET"])
def news_review_detail():
    """新闻审核的详情接口"""
    if request.method == "GET":
        """
        展示新闻审核详情页面的数据
        127.0.0.1:5000/admin/news_review_detail?news_id=1
        """
        # 获取get请求携带的新闻id
        news_id = request.args.get("news_id")

        news = None  # type:News
        if news_id:
            try:
                news = News.query.get(news_id)
            except Exception as e:
                current_app.logger.error(e)
                return abort(404)

        # 新闻对象转字典对象
        news_dict = None
        if news:
            news_dict = news.to_dict()

        data = {
            "news": news_dict
        }

        return render_template("admin/news_review_detail.html", data=data)

    # POST请求：新闻审核逻辑
    """
    1.获取参数
        1.1 news_id: 新闻id， action:审核行为
    2.校验参数
        2.1 非空判断
        2.2 action in ["accept", "reject"]
    3.逻辑处理
        3.0 根据新闻id查询对应新闻
        3.1 根据action进行审核
        通过：
           新闻的状态修改成0： news.status=0
        拒绝：
           获取拒绝原因
           新闻的状态修改成-1： news.status=-1
                             news.reason=reason
        3.2 将上述修改操作保存回数据库                 
    4.返回值
    """
    # 1.1 news_id: 新闻id， action:审核行为
    param_dict = request.json
    news_id = param_dict.get("news_id")
    action = param_dict.get("action")

    # 2.1 非空判断
    if not all([news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    # 2.2 action in ["accept", "reject"]
    if action not in ["accept", "reject"]:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 3.0 根据新闻id查询对应新闻
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="新闻不存在")

    # 3.1 根据action进行审核
    if action == "accept":
        # 通过：
        # 新闻的状态修改成0： news.status=0
        news.status = 0
    else:
        # 拒绝：
        # 获取拒绝原因
        reason = request.json.get("reason")
        if reason:
            # 新闻的状态修改成-1： news.status=-1 & news.reason=reason
            news.status = -1
            news.reason = reason
        else:
            return jsonify(errno=RET.PARAMERR, errmsg="请填写拒绝原因")

    # 3.2 将上述修改操作保存回数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")

    # 4.返回值
    return jsonify(errno=RET.OK, errmsg="OK")


# 127.0.0.1:5000/admin/news_review
@admin_bp.route('/news_review')
def news_review():
    """新闻审核页面展示"""

    # 1.获取要查询的页码
    p = request.args.get("p", 1)
    # 查询关键字（非必传的）
    keywords = request.args.get("keywords")
    # 2.页码校验
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    news_list = []
    current_page = 1
    total_page = 1

    # 查询条件列表 默认查询条件是：审核未通过&未审核的新闻
    filter_list = [News.status != 0]

    if keywords:
        # 关键字是否包含于新闻标题，进行查询
        filter_list.append(News.title.contains(keywords))

    try:
        paginate = News.query.filter(*filter_list).order_by(News.create_time.desc())\
            .paginate(p, constants.ADMIN_NEWS_PAGE_MAX_COUNT, False)

        # 获取当前页码的所有数据
        news_list = paginate.items
        # 当前页码
        current_page = paginate.page
        # 总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return abort(404)

    # 对象列表转字典列表
    news_dict_list = []
    for news in news_list if news_list else []:
        news_dict_list.append(news.to_review_dict())

    # 组织响应数据
    data = {
        "news_list": news_dict_list,
        "current_page": current_page,
        "total_page": total_page
    }

    return render_template("admin/news_review.html", data=data)


# 127.0.0.1:5000/admin/user_list
@admin_bp.route('/user_list')
def user_list():
    """展示管理员页面用户列表"""

    # 1.获取要查询的页码
    p = request.args.get("p", 1)
    # 2.页码校验
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    user_list = []
    current_page = 1
    total_page = 1
    # 3.根据查询条件查询分页数据
    try:
        paginate = User.query.filter(User.is_admin == False).order_by(User.last_login.desc()) \
            .paginate(p, constants.ADMIN_USER_PAGE_MAX_COUNT, False)
        user_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return abort(404)

    # 4.将对象列表转换成字典列表并返回
    user_dict_list = []
    for user in user_list if user_list else None:
        user_dict_list.append(user.to_admin_dict())

    data = {
        "users": user_dict_list,
        "current_page": current_page,
        "total_page": total_page
    }

    return render_template("admin/user_list.html", data=data)


# 127.0.0.1:5000/admin/user_count
@admin_bp.route('/user_count')
def user_count():
    """返回用户统计信息"""
    # 查询总人数
    total_count = 0
    try:
        # 统计普通用户总人数
        total_count = User.query.filter(User.is_admin == False).count()
    except Exception as e:
        current_app.logger.error(e)

    # 查询月新增数
    mon_count = 0
    try:
        """
        time.struct_time(tm_year=2018, tm_mon=12, tm_mday=4, tm_hour=16, tm_min=30, tm_sec=23, tm_wday=1, tm_yday=338, tm_isdst=0)
        
        当前月的第一天：2018-12-01
        下一个月第一天：2019-01-01
        下下一个月第一天：2019-02-01
        
        """
        now = time.localtime()
        # 每一个月的第一天:字符串数据
        mon_begin = '%d-%02d-01' % (now.tm_year, now.tm_mon)
        #  strptime:字符串时间转换成时间格式
        mon_begin_date = datetime.strptime(mon_begin, '%Y-%m-%d')
        # 本月新增人数：用户的创建时间 >= 本月第一天   01--->04表示本月新增人数
        mon_count = User.query.filter(User.is_admin == False, User.create_time >= mon_begin_date).count()
    except Exception as e:
        current_app.logger.error(e)

    # 查询日新增数
    day_count = 0
    try:
        """
        2018-12-04-00:00 ---> 2018-12-04-23:59
        2018-12-05-00:00 ---> 2018-12-05-23:59
        """
        # 一天的开始时间
        day_begin = '%d-%02d-%02d' % (now.tm_year, now.tm_mon, now.tm_mday)
        day_begin_date = datetime.strptime(day_begin, '%Y-%m-%d')
        # 本日新增人数：查询条件是：用户创建时间 > 今天的开始时间，表示今天新增人数
        day_count = User.query.filter(User.is_admin == False, User.create_time > day_begin_date).count()
    except Exception as e:
        current_app.logger.error(e)

    # 查询图表信息
    # 获取到当天2018-12-04-00:00:00时间

    now_date = datetime.strptime(datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
    # 定义空数组，保存数据
    active_date = []
    active_count = []

    """
    开始时间: 2018-12-04-00:00:00 - 0天
    结束时间：2018-12-04-24:00:00 = 开始时间 + 1天
    
    开始时间: 2018-12-04-00:00:00 - 1天  代表12-03
    结束时间：2018-12-03-24:00:00 = 开始时间 + 1天

    开始时间: 2018-12-04-00:00:00 - 2天  代表12-02
    结束时间：2018-12-02-24:00:00 = 开始时间 + 1天

    """
    # 依次添加数据，再反转
    for i in range(0, 31): # 0 1 2.... 30
        # 获取一天的开始时间
        begin_date = now_date - timedelta(days=i)
        # 结束时间：2018-12-04-24:00:00 = 开始时间 + 1天
        end_date = begin_date + timedelta(days=1)
        # 添加每一天的时间到列表中
        active_date.append(begin_date.strftime('%Y-%m-%d'))
        count = 0
        try:
            # 用户最后一次登录时间 > 一天的开始时间
            # 用户最后一次登录时间 < 一天的结束时间
            # 一天内的活跃量
            count = User.query.filter(User.is_admin == False, User.last_login >= begin_date,
                                      User.last_login < end_date).count()
        except Exception as e:
            current_app.logger.error(e)
        # 将每一天的活跃量添加到列表
        active_count.append(count)

    # [12-04, 12-03.....]  --> [11-04, 11-05.....12-04]
    # 日期和数据反转
    active_date.reverse()
    active_count.reverse()

    data = {"total_count": total_count, "mon_count": mon_count, "day_count": day_count, "active_date": active_date,
            "active_count": active_count}

    return render_template('admin/user_count.html', data=data)





# 127.0.0.1:5000/admin/index
@admin_bp.route('/index', methods=['POST', "GET"])
def admin_index():
    return render_template("admin/index.html")


# 127.0.0.1:5000/admin/login
@admin_bp.route('/login', methods=['POST', "GET"])
def admin_login():
    """管理员登录接口"""
    if request.method == 'GET':
        """
        管理员用户登录优化：如果管理员已经登录，再次访问/admin/login,我们就把他引导到/admin/index
        """
        user_id = session.get("user_id")
        is_admin = session.get("is_admin", False)
        # 当前用户登录了，同时还需要是管理员
        if user_id and is_admin:
            return redirect(url_for("admin.admin_index"))
        else:
            return render_template("admin/login.html")

    # POST请求：后端管理员登录逻辑
    """
    1.获取参数
        1.1 username:管理员账号，password未加密密码
    2.校验参数
        2.1 非空判断
    3.逻辑处理
        3.0 根据账号username查询管理员用户是否存在
        3.1 校验密码
        3.2 保存管理员登录信息
    4.返回值
        登录成功
    """
    # 1.1 username:管理员账号，password未加密密码
    param_dict = request.form
    username = param_dict.get("username")
    password = param_dict.get("password")

    # 2.1 非空判断
    if not all([username, password]):
        return render_template("admin/login.html", errmsg="参数不足")

    # 3.0 根据账号username查询管理员用户是否存在
    try:
        admin_user = User.query.filter(User.mobile == username, User.is_admin == True).first()
    except Exception as e:
        current_app.logger.error(e)
        return render_template("admin/login.html", errmsg="查询管理员用户异常")

    if not admin_user:
        return render_template("admin/login.html", errmsg="管理员用户不存在")

    # 3.1 校验密码
    if not admin_user.check_passowrd(password):
        return render_template("admin/login.html", errmsg="密码填写错误")

    # 3.2 保存管理员登录信息
    session["user_id"] = admin_user.id
    session["nick_name"] = username
    session["mobile"] = username
    # 保存管理员身份
    session["is_admin"] = True

    # 4，登录成功,跳转到管理员首页
    return redirect(url_for("admin.admin_index"))













