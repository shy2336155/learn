import qiniu
from flask import current_app, jsonify

from info.utitls.response_code import RET

access_key = "W0oGRaBkAhrcppAbz6Nc8-q5EcXfL5vLRashY4SI"
secret_key = "tsYCBckepW4CqW0uHb9RdfDMXRDOTEpYecJAMItL"
bucket_name = "information"


def pic_storage(data):
    """将图片二进制数据上传到七牛云"""
    # 用户权限鉴定
    q = qiniu.Auth(access_key, secret_key)
    # 图片名称 ，如果不指明七牛云会自动生成一个随机的唯一的图片名称
    # key = 'hello'
    token = q.upload_token(bucket_name)

    if not data:
        return AttributeError("图片数据为空")

    try:
        # 将二进制图片数据上传到七牛云（网络请求有可能失败）
        ret, info = qiniu.put_data(token, None, data)
    except Exception as e:
        current_app.logger.error(e)
        raise e

    print(ret)
    print("---------")
    print(info)
    # 工具类如果产生异常千万别私自处理，应该抛出，方便调用者查询异常所在。
    if info.status_code != 200:
        raise Exception("图片上传到七牛云失败")

    # 返回图片名称
    return ret["key"]


if __name__ == '__main__':
    file = input("请输入图片地址：")
    with open(file, "rb") as f:
        # 读取到图片二进制数据
        data = f.read()
        pic_storage(data)