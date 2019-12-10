from flask import Blueprint

# 1. 创建蓝图  url_prefix="/user" 用户个人中心模块url访问前缀
profile_bp = Blueprint("user", __name__, url_prefix="/user")

# 注意passport模块知道views中的业务逻辑代码
from .views import *