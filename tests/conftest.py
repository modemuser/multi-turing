import random

import pytest

from mt.model import random_instance


@pytest.fixture
def instances():
    rng = random.Random(12345)
    return [random_instance(2, k, rng) for k in (1, 2, 3, 4) for _ in range(40)]
