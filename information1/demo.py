# class person(object):
#
#     def __eq__(self, other):
#         return "查询条件"
#
#
# if __name__ == '__main__':
#     p1 = person()
#     p2 = person()
#     print(p1 == p2)
#
#     filter = [1, 3, 4]
#     print(filter)
#     print(*filter)

# import functools
# # 使用装饰器装饰带视图函数后，视图函数的名称一些注释会发生改变
# # 解决方案：@functools.wraps(func)解决
#
#
# # 普通装饰器
# def user_login_data(func):
#     @functools.wraps(func)
#     def warapper(*args, **kwargs):
#         pass
#     return warapper
#
#
# @user_login_data
# def index():
#     """index"""
#     return "index"
#
#
# @user_login_data
# def news():
#     """news"""
#     return "news"
#
#
# if __name__ == '__main__':
#     print(index.__name__)
#     print(news.__name__)
import random
import datetime
from info import db
from info.models import User
from manager import app


# 添加测试数据
def add_test_users():
    users = []
    # 当前时间
    now = datetime.datetime.now()
    # 生一万个用户
    for num in range(0, 10000):
        try:
            user = User()
            user.nick_name = "%011d" % num
            user.mobile = "%011d" % num
            user.password_hash = "pbkdf2:sha256:50000$SgZPAbEj$a253b9220b7a916e03bf27119d401c48ff4a1c81d7e00644e0aaf6f3a8c55829"
            # 最后一次登录时间（随机时间）12-4 -- 11-4 在过去一个月内时间登录
            user.last_login = now - datetime.timedelta(seconds=random.randint(0, 2678400))
            users.append(user)
            print(user.mobile)
        except Exception as e:
            print(e)
    # 手动开启应用上下文
    with app.app_context():
        # 开启上下文之后，才拥有整个项目的配置，应用对象
        db.session.add_all(users)
        db.session.commit()
    print('OK')

add_test_users()