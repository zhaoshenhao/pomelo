import itertools
import random
import string

_random_suffix = "".join(random.choices(string.ascii_lowercase, k=6))
_name_counter = itertools.count()


def unique_library_name(prefix: str = "test") -> str:
    return f"{prefix}_{_random_suffix}_{next(_name_counter)}"
