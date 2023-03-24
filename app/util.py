import logging

logger = logging.getLogger(__name__)


def threaded_method(func):
    # so we won't miss exceptions
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(e)
            raise e

    return wrapper
