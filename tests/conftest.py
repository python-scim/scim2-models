import json
import sys

import pytest

collect_ignore = [] if sys.version_info >= (3, 14) else ["test_template_strings.py"]


@pytest.fixture
def load_sample():
    def wrapped(filename):
        with open(f"samples/{filename}") as fd:
            return json.load(fd)

    return wrapped
