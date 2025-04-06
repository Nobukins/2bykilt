import logging
import os
import sys
from functools import wraps

class Logger:
    @staticmethod
    def setup(name):
        """統一されたロガーをセットアップ"""
        logger = logging.getLogger(name)
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter('%(levelname)s [%(name)s] %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            level = os.getenv("LOG_LEVEL", "INFO").upper()
            logger.setLevel(getattr(logging, level, logging.INFO))
        return logger

    @staticmethod
    def log_method_calls(logger):
        """メソッド呼び出しを自動でロギングするデコレータ"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                logger.debug(f"CALL: {func.__name__}({', '.join([str(a) for a in args[1:]] + [f'{k}={v}' for k, v in kwargs.items()])})")
                result = func(*args, **kwargs)
                logger.debug(f"RETURN: {func.__name__} -> {result}")
                return result
            return wrapper
        return decorator

    @staticmethod
    def log_async_method_calls(logger):
        """非同期メソッド呼び出しを自動でロギングするデコレータ"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                method_name = func.__name__
                args_str = ', '.join([str(a) for a in args[1:]] + [f'{k}={v}' for k, v in kwargs.items()])
                logger.debug(f"ASYNC CALL: {method_name}({args_str})")
                try:
                    result = await func(*args, **kwargs)
                    logger.debug(f"ASYNC RETURN: {method_name} -> {result}")
                    return result
                except Exception as e:
                    logger.error(f"ASYNC ERROR: {method_name} -> {str(e)}")
                    raise
            return wrapper
        return decorator
