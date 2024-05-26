import json

import pytest


@pytest.fixture
def load_sample():
    def wrapped(filename):
        with open(f"samples/{filename}") as fd:
            return json.load(fd)

    return wrapped
