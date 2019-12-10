from info.models import User
from info.module.passport import passport_bp
from flask import request, current_app, abort, make_response, jsonify, session
from info.utitls.captcha.captcha import captcha
from info import redis_store, constants
from info.utitls.response_code import RET
from info.lib.yuntongxun.sms import CCP
import re
from info import db
from datetime import datetime


# 127.0.0.1:5000/passport/login_out
@passport_bp.route('/login_out', methods=["POST"])
def login_out():
    """退出登录"""

    # 删除session中的用户数据即可
    """
    调用sesion =====>  session_id + secrete_key 加密---> 随机字符串 
     {
        "user_id" ： 1        
     }
    """
    session.pop("user_id", None)
    session.pop("mobile", None)
    session.pop("nick_name", None)
    # 当退出登录的时候需要将管理员的权限记录去掉
    session.pop("is_admin", None)

    return jsonify(errno=RET.OK, errmsg="退出登录成功")


@passport_bp.route('/login', methods=["POST"])
def login():
    """登录后端接口"""
    """
    1. 获取参数
        1.1 mobile：手机号码  password:密码
    2. 参数校验
        2.1 非空判断
        2.2 手机格式校验
    3. 业务逻辑
        3.0 根据mobile查询当前用户是否存在
        存在：进行密码对比
        不存在： 提示注册
        3.1 password未加密的密码再次加密后进行比对
        不相等： 提示密码填写错误
        相等：记录用户登录信息，修改用户最后一次登录时间
    4. 返回登录成功 
    """
    # 1.1 mobile：手机号码  password:密码
    param_dict = request.json
    mobile = param_dict.get("mobile")
    password = param_dict.get("password")
    # 2.1 非空判断
    if not all([mobile, password]):
        current_app.logger.error("参数不足")
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    # 2.2 手机号码格式校验
    if not re.match("1[35789][0-9]{9}", mobile):
        current_app.logger.error("手机格式错误")
        return jsonify(errno=RET.PARAMERR, errmsg="手机格式错误")
    # 3.0 根据mobile查询当前用户是否存在
    try:
        user = User.query.filter(User.mobile == mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")
    if not user:
        # 用户不存在
        return jsonify(errno=RET.NODATA, errmsg="用户不存在")

    # 3.1 password未加密的密码再次加密后进行比对
    # 存在：进行密码对比
    if not user.check_passowrd(password):
        # 不相等： 提示密码填写错误
        return jsonify(errno=RET.DATAERR, errmsg="密码填写错误")

    # 相等：记录用户登录信息，修改用户最后一次登录时间
    session["user_id"] = user.id
    session["mobile"] = mobile
    session["nick_name"] = mobile
    # 修改最后一次登录时间
    user.last_login = datetime.now()

    try:
        # 提交对象的修改操作到数据库
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        # 数据库回滚
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存用户数据异常")

    # 4.返回值
    return jsonify(errno=RET.OK, errmsg="登录成功")


# 127.0.0.1:5000/passport/register
@passport_bp.route('/register', methods=['POST'])
def register():
    """注册后端接口"""
    """
    1. 获取参数（json格式）
        1.1 mobile：手机号码， sms_code:短信验证码， password:密码
    2. 参数校验
       # 2.1 非空判断
       # 2.2 手机号码格式校验
    3. 逻辑处理
        3.1 根据key：SMS_18520340803去redis中获取真实的短信验证码
            有值：从redis数据库删除
            没有值：短信验证码过期了
        3.2 拿用户填写的短信验证码和真实的短信验证码对比
            不相等：提示前端
        3.3 相等： 创建用户对象，并给对应属性赋值，保存到数据库
        3.4 注册成功一般表示登录成功，使用session保存用户基本信息
    4. 返回值
        4.1 返回注册成功
    """
    # 1.1 mobile：手机号码， sms_code:短信验证码， password:密码
    param_dict = request.json
    mobile = param_dict.get("mobile")
    sms_code = param_dict.get("sms_code")
    password = param_dict.get("password")

    # 2.1 非空判断
    if not all([mobile, sms_code, password]):
        current_app.logger.error("参数不足")
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    # 2.2 手机号码格式校验
    if not re.match("1[35789][0-9]{9}", mobile):
        current_app.logger.error("手机格式错误")
        return jsonify(errno=RET.PARAMERR, errmsg="手机格式错误")

    # 3.1 根据key：SMS_18520340803去redis中获取真实的短信验证码
    try:
        real_sms_code = redis_store.get("SMS_%s" % mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询短信验证码数据异常")

    # 有值：从redis数据库删除
    if real_sms_code:
        redis_store.delete("SMS_%s" % mobile)
    else:
        # 没有值：短信验证码过期了
        current_app.logger.error("短信验证码过期")
        return jsonify(errno=RET.NODATA, errmsg="短信验证码过期")

    # 3.2 拿用户填写的短信验证码和真实的短信验证码对比
    if real_sms_code != sms_code:
        # 提示用户请再次填写
        current_app.logger.error("短信验证码填写错误")
        return jsonify(errno=RET.DATAERR, errmsg="短信验证码填写错误")

    # 3.3 相等： 创建用户对象，并给对应属性赋值，保存到数据库
    user = User()
    user.nick_name = mobile
    user.mobile = mobile
    # TODO：密码还未加密处理
    # user.set_password_hash(password)

    # 使用属性get&set方法进行密码加密处理
    user.password = password
    # 记录最后一次登录时间
    user.last_login = datetime.now()

    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        # 数据库回滚
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存用户对象异常")

    # 3.4 注册成功一般表示登录成功，使用session保存用户基本信息
    session["user_id"] = user.id
    session["mobile"] = mobile
    session["nick_name"] = mobile

    # 4.告诉调用者注册成功
    return jsonify(errno=RET.OK, errmsg="注册成功")


# 2.使用蓝图
# 127.0.0.1:5000/passport/image_code?code_id=UUID
@passport_bp.route('/image_code')
def get_image_code():
    """获取验证码图片"""
    """
    1.获取参数
        1.1 获取code_id：唯一编码UUID
    2.校验参数
        2.1 判断code_id是否有值
    3.逻辑处理
        3.1  生成验证码图片 & 生成验证码图片上的真实值
        3.2 根据code_id编号作为key将生成验证码图片上的真实值存储到redis数据，并且设置有效时长（后续接口需要校验）
    4.返回值
        4.1 生成验证码图片,返回给前端
    """
    # 1.1 获取code_id：唯一编码UUID
    code_id = request.args.get("code_id")

    # 2.1 判断code_id是否有值
    if not code_id:
        current_app.logger.error("参数不足")
        abort(403)

    # 3.1 生成验证码图片 & 生成验证码图片上的真实值
    image_name, image_code, image_data = captcha.generate_captcha()
    try:
        # 3.2 根据code_id编号作为key将生成验证码图片上的真实值存储到redis数据，并且设置有效时长（后续接口需要校验）
        redis_store.setex("ImageCode_%s" % code_id, constants.IMAGE_CODE_REDIS_EXPIRES, image_code)
    except Exception as e:
        # 记录日志
        current_app.logger.error(e)
        abort(500)

    # 4.1 生成验证码图片,返回给前端(如果返回的是二进制数据不能兼容所有前端浏览器)
    response = make_response(image_data)
    # 返回数据的类型"image/JPEG"
    response.headers["Content-Type"] = "image/JPEG"
    return response


# 127.0.0.1:5000/passport/sms_code
@passport_bp.route('/sms_code', methods=["POST"])
def send_smscode():
    """发送短信验证码后端接口"""
    """
    1.获取参数
        1.1 mobile: 手机号码  image_code_id:uuid唯一编号  image_code:用户填写图片验证码真实值
    2.校验参数
        2.1 非空判断
        2.2 正则校验手机号码格式
    3.逻辑处理
        3.1 根据image_code_id编号去redis数据库获取正确的图片验证码值，
            3.1.1 real_image_code有值： 从数据库删除（防止多次使用这个值进行校验）
            3.1.2 real_image_code没有有值： 图片验证码过期了
        3.2 然后进行对比校验、
            3.2.1 相等 ：发送短信验证码    
            3.2.2 不相等： 告诉前端图片验证码填写错误（前端再次生成一张图片 ）
             
        TODO: 查询手机号码是否有注册过，不要等到注册的时候在判断（提高用户体验）         
        3.3 送短信验证码细节
            3.3.1 生成6位的随机短信值 ： 123456
            3.3.2 调用封装好ccp短信验证码工具类发送 
            3.3.3 发送短信验证码成功后，保存6位的随机短信值到redis数据库
    4.返回值 
        4.1 发送短信验证码成功
    """

    # import json
    # json.loads(request.data)
    # 1.1 mobile: 手机号码  image_code_id:uuid唯一编号  image_code:用户填写图片验证码真实值
    # 提取前端发送的json格式数据，并且将数据转换成python对象
    param_dict = request.json
    mobile = param_dict.get("mobile")
    image_code = param_dict.get("image_code")
    image_code_id = param_dict.get("image_code_id")
    # 2.1 非空判断
    if not all([mobile, image_code, image_code_id]):
        current_app.logger.error("参数错误")
        # return jsonify({"errno": RET.PARAMERR, "errmsg": "参数错误"})
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    # 2.2 正则校验手机号码格式

    if not re.match("1[35789][0-9]{9}", mobile):
        current_app.logger.error("手机格式错误")
        return jsonify(errno=RET.PARAMERR, errmsg="手机格式错误")

    # 3.1 根据image_code_id编号去redis数据库获取正确的图片验证码值，
    try:
        real_image_code = redis_store.get("ImageCode_%s" % image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询验证码真实值异常")
    # 3.1.1 real_image_code有值： 从数据库删除（防止多次使用这个值进行校验）
    if real_image_code:
        try:
            redis_store.delete("ImageCode_%s" % image_code_id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="删除验证码真实值异常")
    # 3.1.2 real_image_code没有有值： 图片验证码过期了
    else:
        current_app.logger.error("图片验证码真实值过期了")
        return jsonify(errno=RET.NODATA, errmsg="图片验证码真实值过期了")

    # 3.2 然后进行对比校验
    """
    细节：1.忽略大小写  2.real_image_code如果直接获取是二进制形式 设置 decode_responses=True 
    """
    if image_code.lower() != real_image_code.lower():
        # 3.2.2 不相等： 告诉前端图片验证码填写错误（前端再次生成一张图片 ）
        current_app.logger.error("填写图片验证码错误")
        return jsonify(errno=RET.DATAERR, errmsg="填写图片验证码错误")

    # 3.2.1 相等 ：发送短信验证码
    # TODO: 查询手机号码是否有注册过，不要等到注册的时候在判断（提高用户体验）
    # try是会消耗性能的，在关键的代码使用
    try:
        user = User.query.filter(User.mobile == mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询用户数据异常")
    if user:
        # 用户已经注册
        return jsonify(errno=RET.DATAEXIST, errmsg="用户已经注册")

    import random
    # 3.3 送短信验证码细节
    # 3.3.1 生成6位的随机短信值 ： 123456
    # 可能不足6位
    sms_code = random.randint(0, 999999)
    # 不足6位前面用0补足
    sms_code = "%06d" % sms_code

    # 3.3.2 调用封装好ccp短信验证码工具类发送
    """
    参数1： 手机号码
    参数2； {6位的短信验证码值，分钟}
    参数3： 模板id 1：您的验证码为{1}，请于{2}内正确输入，如非本人操作，请忽略此短信。
    """
    try:
        result = CCP().send_template_sms(mobile, {sms_code, constants.SMS_CODE_REDIS_EXPIRES/60}, 1)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="短信验证码发送失败")
    # 判断短信验证码发送返回的结果
    if result == -1:
        current_app.logger.error("短信验证码发送失败")
        return jsonify(errno=RET.THIRDERR, errmsg="短信验证码发送失败")

    print(sms_code)
    # 3.3.3 发送短信验证码成功后，保存6位的随机短信值到redis数据库
    try:
        redis_store.setex("SMS_%s" % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="保存短信验证码异常")

    # 4.返回值
    # 4.1 发送短信验证码成功
    return jsonify(errno=RET.OK, errmsg="发送短信验证码成功")

























