import time
from typing import Callable, Any

class TimeLogger:
    def __init__(self):
        self.tags_times = {}
        self.start_times = {}
    
    def start(self, tag: str) -> None:
        if tag in self.start_times:
            del self.start_times[tag]
        self.start_times[tag] = time.time()
    
    def end(self, tag: str) -> None:
        if tag in self.start_times:
            if not tag in self.tags_times:
                self.tags_times[tag] = []
            self.tags_times[tag].append(time.time() - self.start_times[tag])
            del self.start_times[tag]

    def describe(self) -> None:
        print(' TimeLogger '.center(30, '='))
        for ind, (tag, times) in enumerate(self.tags_times.items()):
            print(f'{ind + 1}) {tag} [count={len(times)}]')
            print(f'min: {min(times):.3f} s, max: {max(times):.3f} s, avg: {sum(times) / len(times):.3f} s')

    @staticmethod
    def track_function(tl: 'TimeLogger') -> Callable:
        # this function creates a decorator on the fly
        # using the TimeLogger instance
        def decorator(func: Callable) -> Callable:
            # when a decorator is attached to a function
            # the decorator is called instead of the function during run time
            # with the attached function as an argument to the decorator
            # then the decorater returns a new function
            # that will be executed in place of the original function
            # which is the wrapper and we can define all our operations in the wrapper
            def wrapper(*args, **kwargs) -> Any:
                # the original function will be called
                # inside the wrapper, so everything runs smoothly
                # as if nothing ever changed
                tag = func.__name__ + ' (func)'
                tl.start(tag)
                res = func(*args, **kwargs)
                tl.end(tag)
                return res
            return wrapper
        return decorator