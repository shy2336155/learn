import logging
from redis import StrictRedis


# 0.自定义项目配置类
class Config(object):
    """项目配置基类"""

    # 开启debug模式
    DEBUG = True

    # mysql数据库配置信息
    # mysql数据库链接配置
    SQLALCHEMY_DATABASE_URI = "mysql://root:xiaoxiaozi@127.0.0.1:3306/information21"
    # 开启数据库跟踪操作
    SQLALCHEMY_TRACK_MODIFICATIONS = True

    # redis数据库配置信息
    REDIS_HOST = "127.0.0.1"
    REDIS_PORT = 6379
    REDIS_NUM = 1

    # 将session存储的数据从`内存`转移到`redis`中存储的配置信息
    SECRET_KEY = "SADLKASJDLAKSJDLSAKJD8AS9"
    # 指明数据库类型需要redis数据库
    SESSION_TYPE = "redis"
    # 创建真实存储数据库的对象进行赋值
    SESSION_REDIS = StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_NUM)
    # session_id是否需要进行加密处理
    SESSION_USE_SIGNER = True
    # 设置数据不需要永久保存，而是根据我们设置的过期时长进行调整
    # SESSION_PERMANENT = False
    # 设置过期时长 默认数据31天过期
    PERMANENT_SESSION_LIFETIME = 86400


class DevelopmentConfig(Config):
    """开发模式的项目配置信息"""
    DEBUG = True
    # 设置日志级别，开发模式一般设置成DEBUG
    LOG_LEVEL = logging.DEBUG


class ProductionConfig(Config):
    """上线模式的项目配置信息"""
    DEBUG = False
    # 设置日志级别，开发模式一般设置成WARNING
    LOG_LEVEL = logging.WARNING


# 提供一个接口给外界使用
# useage: config_dict["development"] -- DevelopmentConfig  传入development参数获取开发模式的配置信息
config_dict = {
    "development": DevelopmentConfig,
    "production": ProductionConfig

}














