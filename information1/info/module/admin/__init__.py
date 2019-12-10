from flask import Blueprint, redirect

# 1.创建蓝图对象
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# 让admin模块知道views文件的存在
from .views import *


# 借助请求钩子在每次请求之前对用户权限判断
@admin_bp.before_request
def is_admin_user():
    """管理员模块的权限判断"""

    print(request.url)
    # http://127.0.0.1:5000/admin/login 表示管理员需要登录，这个请求不应该拦截
    if request.url.endswith("/admin/login"):
        pass
    else:
        # 权限校验
        user_id = session.get("user_id")
        is_admin = session.get("is_admin", False)
        # user_id没有值，表示用户没有登录
        # is_admin == False: 表示不是管理员
        # 是普通用户，应该引导到新闻首页（/）进行登录
        if not user_id or is_admin == False:
            return redirect("/")






