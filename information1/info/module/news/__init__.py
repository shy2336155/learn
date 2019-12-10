from flask import Blueprint

# 1. 创建蓝图  url_prefix="/news" 新闻详情模块url访问前缀
newsdetail_bp = Blueprint("newsdetail_bp", __name__, url_prefix="/news")

# 注意passport模块知道views中的业务逻辑代码
from .views import *