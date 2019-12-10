from flask import Blueprint

# 1.创建蓝图对象
index_bp = Blueprint("index", __name__)

# 让index模块知道views文件的存在
from info.module.index.views import *