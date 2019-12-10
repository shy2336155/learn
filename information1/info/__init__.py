from logging.handlers import RotatingFileHandler
import logging
from flask import Flask, session, render_template, g
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from redis import StrictRedis
from flask_wtf.csrf import CSRFProtect, generate_csrf
from config import config_dict
from info.utitls.common import set_rank_class, user_login_data

# 一开始只是进行声明并没有实质上进行db的初始化
db = SQLAlchemy()
# 声明属性的类型
redis_store = None  # type: StrictRedis


def set_log(config_class):
    """记录项目的日志信息"""
    # 设置日志的记录等级
    # DevelopmentConfig.LOG_LEVEL = DEBUG
    logging.basicConfig(level=config_class.LOG_LEVEL)  # 调试debug级

    # 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限 100M 最多可以记录10个日志文件
    file_log_handler = RotatingFileHandler("logs/log", maxBytes= 1024 * 1024 * 100, backupCount=10)

    # 创建日志记录的格式 日志等级 输入日志信息的文件名 行数 日志信息
    formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')

    # 为刚创建的日志记录器设置日志记录格式
    file_log_handler.setFormatter(formatter)

    # 为全局的日志工具对象（flask app使用的）添加日志记录器
    logging.getLogger().addHandler(file_log_handler)


# 将app的创建使用工厂模式封装起来
# create_app("development") --> DevelopmentConfig -->   对应的就是开发模式的app
# create_app("production") --> ProductionConfig   -->   对应的就是上线模式的app
def create_app(config_name):
    """工厂方法"""
    # 1.创建app对象
    app = Flask(__name__)

    # development -- DevelopmentConfig 根据传入的参数不同获取不同的配置信息
    config_class = config_dict[config_name]

    # 设置日志
    set_log(config_class)

    # 将对于的配置类关联到app身上
    # DevelopmentConfig：对应的就是开发模式的app
    # ProductionConfig： 对应的就是线上模式的app
    app.config.from_object(config_class)

    # 2.创建数据库对象
    # 使用延迟，懒加载的模式：真实的db数据库对象的初始化操作
    db.init_app(app)

    # 3.创建redis对象 -- 延迟加载的思想
    # decode_responses=True 获取的数据转换成字符串
    global redis_store
    redis_store = StrictRedis(host=config_class.REDIS_HOST,
                              port=config_class.REDIS_PORT,
                              db=config_class.REDIS_NUM,
                              decode_responses=True
                              )

    # 4.给项目添加csrf防护机制
    # 提取cookie中的csrf_token
    # 如果有表单提取form表单中的csrf_token，如果前端发送的ajax请求从请求头的X-CSRFToken字段中提取csrf_token
    # 进行值的比对
    CSRFProtect(app)

    # 借助钩子函数请求完毕页面显示的时候就在cookie中设置csrf_token
    @app.after_request
    def set_csrf_token(response):
        # 请求结束后来调用
        # 1. 生成csrf_token随机值
        csrf_token = generate_csrf()
        # 2. 借助response响应对象值设置到cookie中
        response.set_cookie("csrf_token", csrf_token)
        # 3. 返回响应对象
        return response

    # 5.将session存储的数据从`内存`转移到`redis`中存储的
    Session(app)

    # 添加最定义过滤器
    app.add_template_filter(set_rank_class, "set_rank_class")

    @app.errorhandler(404)
    @user_login_data
    def handler_404(e):
        """处理404页面"""
        # 获取当前登录用户数据
        user = g.user
        data = {
            "user_info": user.to_dict() if user else None
        }
        return render_template("news/404.html", data=data)


    # 6.注册index首页的蓝图对象
    # 延迟导入解决循环导入问题
    from info.module.index import index_bp
    app.register_blueprint(index_bp)

    # 登录注册模块蓝图注册
    from info.module.passport import passport_bp
    app.register_blueprint(passport_bp)

    # 新闻详情模块蓝图注册
    from info.module.news import newsdetail_bp
    app.register_blueprint(newsdetail_bp)

    # 用户中心模块蓝图注册
    from info.module.profile import profile_bp
    app.register_blueprint(profile_bp)

    # 后台管理模块蓝图注册
    from info.module.admin import admin_bp
    app.register_blueprint(admin_bp)

    return app
