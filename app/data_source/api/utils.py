import base64
import logging
import concurrent.futures
from functools import lru_cache
from io import BytesIO
from typing import Optional
import time
from functools import wraps

import requests

def rate_limit(*, allowed_per_second: int):
    max_period = 1.0 / allowed_per_second
    def decorate(func):
        last_call = [time.perf_counter()]
        @wraps(func)
        def limit(*args, **kwargs):
            with rate_limiter(last_call, max_period):
                return func(*args, **kwargs)
        return limit
    return decorate


def rate_limiter(last_call, max_period):
    class RateLimiter:
        def __enter__(self):
            elapsed = time.perf_counter() - last_call[0]
            hold = max_period - elapsed
            if hold > 0:
                time.sleep(hold)
        def __exit__(self, exc_type, exc_val, exc_tb):
            last_call[0] = time.perf_counter()
    return RateLimiter()


logger = logging.getLogger(__name__)


def snake_case_to_pascal_case(snake_case_string: str):
    """Converts a snake case string to a PascalCase string"""
    components = snake_case_string.split('_')
    return "".join(x.title() for x in components)


def _wrap_with_try_except(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception("Failed to parse data source", exc_info=e)
            raise e

    return wrapper


def parse_with_workers(method_name: callable, items: list, **kwargs):
    workers = 10  # should be a config value

    logger.info(f'Parsing {len(items)} documents using {method} (with {workers} workers)...')

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        for i in range(workers):
            futures.append(executor.submit(_wrap_with_try_except(method), items[i::workers], **kwargs))
        concurrent.futures.wait(futures)
        for w in futures:
            e = w.exception()
            if e:
                logging.exception("Worker failed", exc_info=e)


@lru_cache(maxsize=512)
def get_confluence_user_image(image_url: str, token: str) -> Optional[str]:
    try:
        if "anonymous.svg" in image_url:
            image_url = image_url.replace(".svg", ".png")

        response = requests.get(url=image_url, timeout=1, headers={'Accept': 'application/json',
                                                                   "Authorization": f"Bearer {token}"})
        image_bytes = BytesIO(response.content)
        return f"data:image/jpeg;base64,{base64.b64encode(image_bytes.getvalue()).decode()}"
    except:
        logger.warning(f"Failed to get confluence user image {image_url}")

