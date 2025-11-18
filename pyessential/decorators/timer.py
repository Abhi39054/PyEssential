import time
from functools import wraps

def timeit(func):
    """Decorator to measure and print function execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        print(f"[{func.__name__}] executed in {execution_time:.4f} seconds.")
        return result
    return wrapper