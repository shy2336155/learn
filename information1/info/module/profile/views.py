from info import db
from info.models import User, News, Category
from info.utitls.response_code import RET
from . import profile_bp
from flask import render_template, g, request, jsonify, session, current_app
from info.utitls.common import user_login_data
from info.utitls.pic_storage import pic_storage
from info import constants


# 127.0.0.1:5000/user/user_follow?p=1
@profile_bp.route('/user_follow')
@user_login_data
def user_follow():
    """新闻列表数据展示"""

    user = g.user
    # 用户登录才查询用户发布的新闻列表
    # 注意：第一次跳转的时候没有携带p页码，使用默认值
    p = request.args.get("p", 1)

    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    user_list = []
    current_page = 1
    total_page = 1
    if user:
        """
        user.followed：当前登录用户的关注列表
        犹豫被修饰成dynamic属性
        user.followed如果真是用到数据返回是一个列表
        user.followed只是去查询了返回一个查询对象
        """
        try:
            paginate = user.followed.paginate(p, constants.USER_FOLLOWED_MAX_COUNT, False)
            # 当前页码所有数据
            user_list = paginate.items
            # 当前页码
            current_page = paginate.page
            # 总页数
            total_page = paginate.pages
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")

    # 用户对象列表转换成字典列表
    user_dict_list = []
    for user in user_list if user_list else []:
        user_dict_list.append(user.to_dict())

    # 组织返回数据
    data = {
        "users": user_dict_list,
        "current_page": current_page,
        "total_page": total_page
    }

    return render_template("profile/user_follow.html", data=data)


# 127.0.0.1:5000/user/news_list?p=1
@profile_bp.route('/news_list')
@user_login_data
def news_list():
    """新闻列表数据展示"""

    user = g.user
    # 用户登录才查询用户发布的新闻列表
    # 注意：第一次跳转的时候没有携带p页码，使用默认值
    p = request.args.get("p", 1)

    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    news_list = []
    current_page = 1
    total_page = 1
    if user:
        # collection_news设置了 lazy="dynamic"
        # 如果真实用到数据的时候，返回的是一个新闻对象列表： [new1, new2,....]
        # 没有真实使用，返回的是查询对象
        try:
            paginate = News.query.filter(News.user_id == user.id).paginate(p, constants.USER_COLLECTION_MAX_NEWS, False)
            # 当前页码所有数据
            news_list = paginate.items
            # 当前页码
            current_page = paginate.page
            # 总页数
            total_page = paginate.pages
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")

    # 新闻对象列表转换成字典列表
    news_dict_list = []
    for news in news_list if news_list else []:
        news_dict_list.append(news.to_review_dict())

    # 组织返回数据
    data = {
        "news_list": news_dict_list,
        "current_page": current_page,
        "total_page": total_page
    }

    return render_template("profile/user_news_list.html", data=data)


# 127.0.0.1:5000/user/news_release
@profile_bp.route('/news_release', methods=["POST", "GET"])
@user_login_data
def news_release():
    """新闻发布页面展示&发布新闻接口"""
    if request.method == "GET":

        # 查询分类数据给前端展示
        try:
            categories = Category.query.all()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询分类数据异常")

        # 对象列表转字典列表
        category_dict_list = []
        for category in categories if categories else []:
            category_dict_list.append(category.to_dict())

        # 删除`最新`分类
        category_dict_list.pop(0)
        data ={
            "categories": category_dict_list
        }

        return render_template("profile/user_news_release.html", data=data)

    # POST请求：发布新闻
    """
    1.获取参数
        1.1 title:标题，cid:分类id，digest:摘要，user:当前用户
            index_image:新闻主图片，content:内容，source：来源（默认个人发布）
    2.校验参数
        2.1 非空判断
    3.逻辑处理
        3.0 将图片上传到七牛云
        3.1 创建新闻对象，给各个属性赋值
        3.2 保存回数据库
    4.返回值
    """
    # 1.1 title:标题，cid:分类id，digest:摘要，user:当前用户
    # index_image:新闻主图片，content:内容，source：来源（默认个人发布）
    # 因为前段使用ajaxSubmit所有数据是form表单提交的
    params_dict = request.form
    title = params_dict.get("title")
    cid = params_dict.get("category_id")
    digest = params_dict.get("digest")
    # 注意：图片从files中提取数据
    index_image = request.files.get("index_image")
    content = params_dict.get("content")
    user = g.user
    source = "个人发布"

    # 2.1 非空判断
    if not all([title, cid, digest, index_image, content]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    image_data = index_image.read()

    # 3.0 将图片上传到七牛云
    try:
        image_name = pic_storage(image_data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="上传图片到七牛云异常")
    # 3.1 创建新闻对象，给各个属性赋值
    news = News()
    news.title = title
    news.category_id = cid
    news.digest = digest
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + image_name
    news.content = content
    news.source = source
    # 当前用户发布的新闻
    news.user_id = user.id
    # 默认发布的新闻是审核中
    news.status = 1

    # 3.2 保存回数据库
    try:
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存用户对象异常")

    # 4.返回值
    return jsonify(errno=RET.OK, errmsg="发布新闻成功")


# 127.0.0.1:5000/user/news_collect?p=2
@profile_bp.route('/news_collect')
@user_login_data
def news_collect():
    """用户收藏新闻列表数据查询"""
    user = g.user
    # 用户登录才查询用户收藏的新闻
    # 注意：第一次跳转的时候没有携带p页码，使用默认值
    p = request.args.get("p", 1)

    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    collection_news_list = []
    current_page = 1
    total_page = 1
    if user:
        #collection_news设置了 lazy="dynamic"
        # 如果真实用到数据的时候，返回的是一个新闻对象列表： [new1, new2,....]
        # 没有真实使用，返回的是查询对象
        try:
            paginate = user.collection_news.paginate(p, constants.USER_COLLECTION_MAX_NEWS, False)
            # 当前页码所有数据
            collection_news_list = paginate.items
            # 当前页码
            current_page = paginate.page
            # 总页数
            total_page = paginate.pages
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")

    # 新闻对象列表转换成字典列表
    news_dict_list = []
    for news in collection_news_list if collection_news_list else []:
        news_dict_list.append(news.to_review_dict())

    # 组织返回数据
    data = {
        "collections": news_dict_list,
        "current_page": current_page,
        "total_page": total_page
    }

    return render_template("profile/user_collection.html", data=data)


# 127.0.0.1:5000/user/pass_info
@profile_bp.route('/pass_info', methods=["POST", "GET"])
@user_login_data
def pass_info():
    """修改密码接口"""
    user = g.user
    if request.method == 'GET':
        return render_template("profile/user_pass_info.html")

    # POST请求修改密码
    """
    1.获取参数
        1.1 old_password:旧密码， new_password:新密码， user:用户对象
    2.校验参数
        2.1 非空判断
    3.逻辑处理
        3.0 判断旧密码是否填写正常
        3.1 将新密码赋值给user对象
        3.2 保存回数据库
    4.返回值
    """
    # 1.1 old_password:旧密码， new_password:新密码， user:用户对象
    param_dict = request.json
    old_password = param_dict.get("old_password")
    new_password = param_dict.get("new_password")
    # 2.1 非空判断
    if not all([old_password, new_password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    # 3.0 判断旧密码是否填写正常
    if not user.check_passowrd(old_password):
        return jsonify(errno=RET.DATAERR, errmsg="旧密码填写错误")

    # 3.1 将新密码赋值给user对象
    user.password = new_password

    # 3.2 保存回数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")

    # 4.返回值
    return jsonify(errno=RET.OK, errmsg="修改密码成功")


# 127.0.0.1:5000/user/pic_info
@profile_bp.route('/pic_info', methods=["POST", "GET"])
@user_login_data
def pic_info():
    """修改用户头像接口"""
    user = g.user
    if request.method == 'GET':
        return render_template("profile/user_pic_info.html")

    # POST请求: 修改用户头像
    """
    1.获取参数
        1.1 pic：图片数据，user:当前用户
    2.校验参数
        2.1 非空判断
    3.逻辑处理
        3.0 调用七牛云工具将图片数据上传到七牛云，返回一个图片名称
        3.1 将图片名称保存到用户对象avatar_url身上
        3.2 返回完整的图片url
    4.返回值
    """
    # 1.1 pic：图片数据，user:当前用户 read():将图片文件转换成二进制数据
    # 注意：前后端的key保持一致：avatar
    pic_data = request.files.get("avatar").read()

    # 非空判断
    if not pic_data:
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")
    # 3.0 调用七牛云工具将图片数据上传到七牛云，返回一个图片名称
    try:
        pic_name = pic_storage(pic_data)
    except Exception as e:
        current_app.logger.error(e)
        # 第三方框架异常
        return jsonify(errno=RET.THIRDERR, errmsg="上传图片到七牛云异常")

    # 3.1 将图片名称保存到用户对象avatar_url身上

    """
    constants.QINIU_DOMIN_PREFIX + 图片名称  ： 一旦前缀发生改变其他所有地方都需要跟着变
    图片名称 
    """
    user.avatar_url = pic_name

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存用户图片数据异常")
    # 3.2 返回完整的图片url
    full_url = constants.QINIU_DOMIN_PREFIX + pic_name

    # 4.返回完整的url
    data = {
        "avatar_url": full_url
    }
    return jsonify(errno=RET.OK, errmsg="修改用户头像数据成功", data=data)


# 127.0.0.1:5000/user/base_info
@profile_bp.route('/base_info', methods=["POST", "GET"])
@user_login_data
def base_info():
    """展示/修改用户基本资料接口"""
    user = g.user

    if request.method == 'GET':
        data = {
            "user_info": user.to_dict() if user else None
        }
        return render_template("profile/user_base_info.html", data=data)

    """
    1.获取参数
        1.1 signature:个性签名，nick_name:昵称，gender：性别
    2.校验参数
        2.1 非空判断
    3.逻辑处理
        3.0 修改用户对象的属性
        3.1 保存回数据库 
    4.返回值
    """
    # 1.1 signature:个性签名，nick_name:昵称，gender：性别
    param_dict = request.json
    signature = param_dict.get("signature")
    nick_name = param_dict.get("nick_name")
    gender = param_dict.get("gender")

    # 2.1 非空判断
    if not all([signature, nick_name, gender]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    if gender not in ["MAN","WOMAN"]:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    # 注意：别的用户对象昵称一样也会重复，需要查询下
    user_list = User.query.filter(User.nick_name == nick_name).all()
    if user_list:
        return jsonify(errno=RET.DATAEXIST, errmsg="用户昵称已经存在")

    # 3.0 修改用户对象的属性
    user.signature = signature
    user.gender = gender
    user.nick_name = nick_name
    # 修改session用户数据
    session["nick_name"] = nick_name

    # 3.1 保存回数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存用户对象异常")

    # 4.返回成功
    return jsonify(errno=RET.OK, errmsg="修改用户数据成功")


# 127.0.0.1:5000/user/info
@profile_bp.route('/info')
@user_login_data
def user_info():
    """用户个人中心"""
    user = g.user
    data = {
        "user_info": user.to_dict() if user else None
    }
    return render_template("profile/user.html", data=data)
