import asyncio
import concurrent.futures
from functools import partial

# Create thread pool for blocking operations
# Max workers = 2 to prevent overloading CPU with multiple FFmpeg processes
executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

async def run_in_executor(func, *args, **kwargs):
    """
    Run blocking function in thread pool executor

    Args:
        func: Blocking function to run
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Result from blocking function
    """
    loop = asyncio.get_event_loop()
    if kwargs:
        func = partial(func, **kwargs)
    return await loop.run_in_executor(executor, func, *args)
