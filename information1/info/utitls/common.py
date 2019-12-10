from flask import session, current_app, jsonify, g
from info.utitls.response_code import RET


def set_rank_class(index):
    # 根据传入的下标返回不同的样式字符串
    if index == 1:
        return "first"
    elif index == 2:
        return "second"
    elif index == 3:
        return "third"
    else:
        return ""


import functools


# 使用装饰器装饰带视图函数后，视图函数的名称一些注释会发生改变
# 解决方案：@functools.wraps(func)解决
# g：能临时保存本次请求的内容
# 传入参数是视图函数名称
def user_login_data(view_func):
    @functools.wraps(view_func)
    def wrapper(*args, **kwargs):

        # 1. 实现需要装饰的内容逻辑
        user_id = session.get("user_id")
        # 延迟导入解决循环导入问题
        from info.models import User

        # 根据user_id查询用户对象
        user = None
        if user_id:
            try:
                user = User.query.get(user_id)
            except Exception as e:
                current_app.logger.error(e)
                return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")
        # 借助g对象临时保存user
        g.user = user

        # 2. 原有函数的逻辑
        result = view_func(*args, **kwargs)
        return result

    return wrapper