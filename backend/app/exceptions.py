class AppException(Exception):
    def __init__(self, message: str, code: int = 5000, detail: str = ""):
        self.message = message
        self.code = code
        self.detail = detail
        super().__init__(message)
