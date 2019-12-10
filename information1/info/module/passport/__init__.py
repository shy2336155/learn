from flask import Blueprint

# 1. 创建蓝图  url_prefix="/passport" 登录注册模块url访问前缀
passport_bp = Blueprint("passport", __name__, url_prefix="/passport")

# 注意passport模块知道views中的业务逻辑代码
from .views import *