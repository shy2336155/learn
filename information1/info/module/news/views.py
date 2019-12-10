from info import constants, db
from info.models import User, News, Category, Comment, CommentLike
from info.utitls.response_code import RET
from . import newsdetail_bp
from flask import render_template, session, current_app, jsonify, g, request
from info.utitls.common import user_login_data


# 127.0.0.1:5000/news/followed_user
@newsdetail_bp.route('/followed_user', methods=['POST'])
@user_login_data
def followed_user():
    """关注/取消关注"""
    """
    1.获取参数
        1.1 user:当前登录的用户, user_id:新闻作者id，action:关注、取消关注行为
    2.校验参数
        2.1 非空判断
    3.逻辑处理
        3.0 根据user_id查询当前新闻的作者对象
        3.1 关注：
            1.author作者添加到当前用户的关注列表中:
              user.followed.append(author)
              
            2.user当前用户添加作者粉丝列表:
              author.followers.append(user)
           
        3.2 取消关注：author作者从到当前用户的关注列表中移除 or user当前用户从添加作者粉丝列表移除
        3.3 将上述修改操作保存回数据库
    4.返回值
    """
    # 1.1 user:当前登录的用户, user_id:新闻作者id，action:关注、取消关注行为
    user = g.user
    user_id = request.json.get("user_id")
    action = request.json.get("action")

    # 2.1 非空判断
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")
    if not all([user_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    if action not in ["follow", "unfollow"]:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 3.0 根据user_id查询当前新闻的作者对象
    try:
        author = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")
    if not author:
        return jsonify(errno=RET.NODATA, errmsg="作者不存在")

    """
    # 3.1 关注：
    #             1.author作者添加到当前用户的关注列表中:
    #               user.followed.append(author)
    #               
    #             2.user当前用户添加作者粉丝列表:
    #               author.followers.append(user)
    """
    if action == "follow":
        if user in author.followers:
            return jsonify(errno=RET.DATAEXIST, errmsg="已经关注不能重复关注")
        else:
            # 把当前用户添加到作者的粉丝列表：表示当前用户关注了作者
            author.followers.append(user)
    # 3.2 取消关注：author作者从到当前用户的关注列表中移除 or user当前用户从添加作者粉丝列表移除
    else:
        # 只有用户已经在关注列表中才有资格取消关注
        if user in author.followers:
            author.followers.remove(user)

    # 3.3 将上述修改操作保存回数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存关注信息对象异常")

    return jsonify(errno=RET.OK, errmsg="ok")


# 127.0.0.1:5000/news/comment_like
@newsdetail_bp.route('/comment_like', methods=["POST"])
@user_login_data
def comment_like():
    """点赞、取消点赞后端接口"""
    """
    1.获取参数
        1.1 user:用户对象，comment_id:评论id，action:点赞和取消点赞的行为
    2.校验参数
        2.1 非空判断
        2.2 action in ["add", "remove"]
    3.逻辑处理
        3.0 comment_id查询出当前评论对象
        3.1 根据action行为点赞或者取消点赞
        点赞：创建CommentLike对象，将属性赋值
        取消点赞：CommentLike对象从数据库删除
    4.返回值
        登录成功
    """

    # 1.1 user:用户对象，comment_id:评论id，action:点赞和取消点赞的行为
    user = g.user
    if not user:
        # 用户未登录
        current_app.logger.error("用户未登录")
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    param_dict = request.json
    comment_id = param_dict.get("comment_id")
    action = param_dict.get("action")
    # 2.1 非空判断
    if not all([comment_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    # 2.2 action in ["add", "remove"]
    if action not in ["add", "remove"]:
        current_app.logger.error("参数错误")
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 3.0 comment_id查询出当前评论对象
    try:
        comment = Comment.query.get(comment_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询评论对象异常")

    if not comment:
        return jsonify(errno=RET.NODATA, errmsg="评论不存在，不允许点赞")

    # 3.1 根据action行为点赞或者取消点赞
    if action == "add":
        comment_like = None
        try:
            # 查询当前用户对当前这条评论是否点赞
            comment_like = CommentLike.query.filter(CommentLike.comment_id == comment_id,
                                                    CommentLike.user_id == user.id
                                                    ).first()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询评论点赞中间表对象异常")
        # 当前用户没有点赞
        if not comment_like:
            # 点赞：创建CommentLike对象，将属性赋值
            comment_like_obj = CommentLike()
            # 当前用户点赞
            comment_like_obj.user_id = user.id
            # 对当前评论点赞
            comment_like_obj.comment_id = comment_id

            # 评论对象的点赞数量累加
            comment.like_count += 1
            db.session.add(comment_like_obj)
    else:
        # 取消点赞：CommentLike对象从数据库删除
        comment_like = None
        try:
            # 查询当前用户对当前这条评论是否点赞
            comment_like = CommentLike.query.filter(CommentLike.comment_id == comment_id,
                                                    CommentLike.user_id == user.id
                                                    ).first()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询评论点赞中间表对象异常")

        # 当前用户已经当前评论点过赞，才有资格取消点赞
        if comment_like:
            db.session.delete(comment_like)
            # 评论对象的点赞数量减一
            comment.like_count -= 1

    # 将上述点赞,取消点赞的修改操作保存回数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        # 回滚
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")
    # 4.返回值
    return jsonify(errno=RET.OK, errmsg="OK")


# 127.0.0.1:5000/news/news_comment
@newsdetail_bp.route('/news_comment', methods=["POST"])
@user_login_data
def news_comment():
    """主评论、子评论后端接口"""
    """
    1.获取参数
        1.1 user:当前登录的用户，news_id:新闻id，comment:评论内容，parent_id:主评论id（非必传）
    2.校验参数
        2.1 非空判断
    3.逻辑处理
        3.0 根据news_id查询出新闻对象(本身可以直接使用news_id给comment赋值，但是防止绕开前端发送请求的时候新闻不存在情况发送)
        3.1 创建评论模型
        3.2 保存到数据库
    4.返回值
        登录成功
    """
    # 1.1 user:当前登录的用户，news_id:新闻id，comment:评论内容，parent_id:主评论id（非必传）
    user = g.user
    if not user:
        # 用户未登录
        current_app.logger.error("用户未登录")
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    param_dict = request.json
    news_id = param_dict.get("news_id")
    comment_str = param_dict.get("comment")
    # 如果有值表示是子评论，反之就是主评论
    parent_id = param_dict.get("parent_id")

    # 2.1 非空判断
    if not all([news_id, comment_str]):
        current_app.logger.error("参数不足")
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    # 3.0 根据news_id查询出新闻对象
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询新闻对象异常")

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="新闻不存在，不能发表评论")

    # 3.1 创建评论模型，并给各个属性赋值
    comment = Comment()
    # 那个用户发表评论
    comment.user_id = user.id
    # 评论的那条新闻
    comment.news_id = news.id
    # 评论内容
    comment.content = comment_str

    if parent_id:
        # 子评论
        comment.parent_id = parent_id

    # 3.2 保存到数据库
    try:
        db.session.add(comment)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        # 回滚
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存评论对象异常")

    # 4.返回值
    # 注意：评论完毕需要返回数据给前端显示
    return jsonify(errno=RET.OK, errmsg="OK", data=comment.to_dict())


# 127.0.0.1:5000/news/news_collect
@newsdetail_bp.route('/news_collect', methods=["POST"])
@user_login_data
def news_collect():
    """收藏/取消收藏的后端接口"""
    """
    1.获取参数
        1.1 news_id:新闻id, user:当前登录的用户对象， action:收藏、取消收藏的行为
    2.校验参数
        2.1 非空判断
        2.2 约定action行为：action in ["collect", "cancel_collect"]
    3.逻辑处理
        3.0 根据新闻id获取新闻对象
        3.1 根据action行为判断是否收藏
        收藏：将新闻对象添加到用户收藏列表
        取消收藏：将新闻对象从用户收藏列表移除（前提：新闻已经在用户收藏列表才去取消收藏）
        3.2 修改操作保存到数据库
    4.返回值
        登录成功
    """
    # 1.1 news_id:新闻id, user:当前登录的用户对象， action:收藏、取消收藏的行为
    # 获取当前登录的用户
    user = g.user
    if not user:
        # 用户未登录
        current_app.logger.error("用户未登录")
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    params_dict = request.json
    news_id = params_dict.get("news_id")
    action = params_dict.get("action")

    # 2.1 非空判断
    if not all([news_id, action]):
        current_app.logger.error("参数不足")
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    # 2.2 约定action行为：action in ["collect", "cancel_collect"]
    if action not in ["collect", "cancel_collect"]:
        current_app.logger.error("参数错误")
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 3.0 根据新闻id获取新闻对象
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询新闻对象异常")

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="新闻不存在")

    # 3.1 根据action行为判断是否收藏
    if action == "collect":
        # 收藏：将新闻对象添加到用户收藏列表
        user.collection_news.append(news)
    else:
        # 取消收藏：将新闻对象从用户收藏列表移除（前提：新闻已经在用户收藏列表才去取消收藏）
        # 新闻在用户收藏列表中
        if news in user.collection_news:
            user.collection_news.remove(news)

    # 3.2 修改操作保存到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        # 回滚
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")

    # 4.返回值
    return jsonify(errno=RET.OK, errmsg="OK")


# 127.0.0.1/news/1  1：代表新闻id
@newsdetail_bp.route('/<int:news_id>')
@user_login_data
def get_news_detail(news_id):
    """展示新闻详情页面"""
    # ----------------1. 查询用户登录信息，进行展示------------------------
    # 获取当前登录用户的user_id
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
        news_dict1 = news_obj.to_dict()
        news_dict_list.append(news_dict1)
    # ----------------3. 根据新闻id查询新闻数据 ------------------------
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询新闻对象异常")

    news_dict = None
    # 新闻对象转字典
    if news:
        news_dict = news.to_dict()

    # 标志当前用户是否收藏过该新闻，默认中：False表示没有收藏
    is_collected = False
    # 标志当前用户是否关注过新闻作者，默认值：False表示没有关注
    is_followed = False


    # 当前用户处于登录状态才查询是否收藏
    if user:
        # ----------------4. 查询当前用户是否有收藏新闻------------------------
        # 当前新闻是否在当前用户新闻收藏列表中
        if news in user.collection_news:
            is_collected = True

    # 查询当前新闻的作者
    try:
        author = User.query.filter(User.id == news.user_id).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")
    """
    user: 当前登录用户
    author：当前新闻作者
    user.followed: 当前登录用户的关注列表
    author.followers ：作者的粉丝列表
    当前用户关注过作者表示形式：
        1.author in user.followed   作者在当前用户的关注列表中
        2.user in author.followers  当前用户是否在作者的粉丝列表中
    """
    # 作者和登录用户都存在
    if user and author:
        # 作者在当前用户的关注列表中
        if author in user.followed:
            is_followed = True

    # ----------------5.获取新闻评论列表数据 ------------------------
    try:
        news_comment_list = Comment.query.filter(Comment.news_id == news_id)\
            .order_by(Comment.create_time.desc()).all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")

    commentlike_id_list = []
    if user:
        # ----------------6.查询当前登录用户具体对那几条评论点过赞 ------------------------
        # 1. 查询出当前新闻的所有评论，取得所有评论的id —>  list[1,2,3,4,5,6]
        # news_comment_list：评论对象列表
        comment_id_list = [comment.id for comment in news_comment_list]

        # 2. 再通过评论点赞模型(CommentLike)查询当前用户点赞了那几条评论  —>[模型1,模型2...]
        try:
            commentlike_obj_list = CommentLike.query.filter(CommentLike.comment_id.in_(comment_id_list),
                                     CommentLike.user_id == user.id
                                     ).all()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")
        # 3. 遍历上一步的评论点赞模型列表，获取所以点赞过的评论id（comment_like.comment_id）
        commentlike_id_list = [commentlike_obj.comment_id for commentlike_obj in commentlike_obj_list]


    # 对象列表转字典列表
    comment_dict_list = []
    for comment_obj in news_comment_list if news_comment_list else []:
        # 评论对象转字典
        comment_dict = comment_obj.to_dict()
        comment_dict["is_like"] = False
        # 遍历每一个评论对象获取其id对比看是否在评论点赞列表中
        # comment_obj1.id == 1 ==> in [1,3,5] ==> is_like=True
        # comment_obj2.id == 2 ==> in [1,3,5] ==> is_like=False
        # comment_obj3.id == 3 ==> in [1,3,5] ==> is_like=True
        if comment_obj.id in commentlike_id_list:
            comment_dict["is_like"] = True
        comment_dict_list.append(comment_dict)

    # 首页数据字典
    data = {
        "user_info": user.to_dict() if user else None,
        "news_rank_list": news_dict_list,
        "news": news_dict,
        "is_collected": is_collected,
        "is_followed": is_followed,
        "comments": comment_dict_list
    }
    return render_template("news/detail.html", data=data)