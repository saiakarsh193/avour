import time
from typing import Callable, Any, List, Union

def oper_with_default(oper: Callable, a: float, b: float) -> float:
    if a == None:
        return b
    if b == None:
        return a
    return oper(a, b)

class TimeLogger:
    def __init__(self):
        self.tag_meta = {}
        self.start_times = {}
    
    def start(self, tag: str) -> None:
        if tag in self.start_times:
            del self.start_times[tag]
        self.start_times[tag] = time.time()

    def end(self, tag: str) -> None:
        if tag in self.start_times:
            dt = time.time() - self.start_times[tag]
            del self.start_times[tag]
            if not tag in self.tag_meta:
                self.tag_meta[tag] = {'count': 0, 'sum': 0, 'min': None, 'max': None}
            self.tag_meta[tag]['count'] += 1
            self.tag_meta[tag]['sum'] += dt
            self.tag_meta[tag]['min'] = oper_with_default(min, self.tag_meta[tag]['min'], dt)
            self.tag_meta[tag]['max'] = oper_with_default(max, self.tag_meta[tag]['max'], dt)

    def describe(self) -> None:
        print(' TimeLogger '.center(30, '='))
        for ind, (tag, meta) in enumerate(self.tag_meta.items()):
            print(f'{ind + 1}) {tag} [count={meta['count']}]')
            print(f'min: {meta['min']:.3f} s, max: {meta['max']:.3f} s, avg: {meta['sum'] / meta['count']:.3f} s')

    @staticmethod
    def track_function(tl: 'TimeLogger', override_tag: str = None) -> Callable:
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
                if override_tag != None:
                    tag = override_tag
                tl.start(tag)
                res = func(*args, **kwargs)
                tl.end(tag)
                return res
            return wrapper
        return decorator

def edit_distance(str1: Union[str, List], str2: Union[str, List]) -> int:
    m, n = len(str1), len(str2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        for j in range(n + 1):
            if i == 0:
                dp[i][j] = j
            elif j == 0:
                dp[i][j] = i
            elif str1[i - 1] == str2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return dp[m][n]