from flask import current_app
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from info import create_app, db

# 从单一职责的原则来考虑，manager文件只需要启动项目，其余不相关的代码都应该抽取出去

# 调用工厂方法 根据传入的参数不同获取不同配置的app。方便后期维护
from info.models import User

app = create_app("development")

# 6.创建管理类
manager = Manager(app)

# 7.创建数据库迁移对象
Migrate(app, db)

# 8.添加迁移指令
manager.add_command("db", MigrateCommand)

"""
使用方式：
    python manager.py createsuperuser -n "admin" -p "123456"
    python manager.py createsuperuser --name "admin" --password "123456"
"""

@manager.option("-n", "--name", dest="name")
@manager.option("-p", "--password", dest="password")
def createsuperuser(name, password):
    """创建管理员用户"""

    if not all([name, password]):
        return "参数不足"

    # 创建管理员对象
    user = User()
    user.mobile = name
    user.password = password
    user.nick_name = name
    user.is_admin = True

    # 添加到数据库
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return "保存管理员用户异常"

    return "创建管理员用户成功"


if __name__ == '__main__':
    # app.run()
    # 9.使用管理对象运行flask项目
    manager.run()