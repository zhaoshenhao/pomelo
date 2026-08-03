class AppException(Exception):
    def __init__(self, message: str, code: int = 5000, detail: str = ""):
        self.message = message
        self.code = code
        self.detail = detail
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(message=message, code=4004)


class BadRequestError(AppException):
    def __init__(self, message: str = "请求参数错误"):
        super().__init__(message=message, code=1000)


class AuthError(AppException):
    def __init__(self, message: str = "认证失败"):
        super().__init__(message=message, code=1001)


class ForbiddenError(AppException):
    def __init__(self, message: str = "权限不足"):
        super().__init__(message=message, code=1002)


class ConflictError(AppException):
    def __init__(self, message: str = "资源冲突"):
        super().__init__(message=message, code=2000)


class BusinessError(AppException):
    def __init__(self, message: str = "业务逻辑错误"):
        super().__init__(message=message, code=2000)
