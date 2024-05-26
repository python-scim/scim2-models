import json

import pytest


@pytest.fixture
def load_sample():
    def wrapped(filename):
        with open(f"tests/fixtures/{filename}") as fd:
            return json.load(fd)

    return wrapped
