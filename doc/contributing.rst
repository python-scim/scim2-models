Contribution
============

Contributions are welcome!

The repository is hosted at `github.com/python-scim/scim2-models <https://github.com/python-scim/scim2-models>`_.

Discuss
-------

If you want to implement a feature or a bugfix, please start by discussing it with us on
the `bugtracker <https://github.com/python-scim/scim2-models/issues>`_.

Unit tests
----------

To run the tests, you just can run `uv run pytest` and/or `tox` to test all the supported python environments.
Everything must be green before patches get merged.

The test coverage is 100%, patches won't be accepted if not entirely covered. You can check the
test coverage with ``uv run pytest --cov --cov-report=html`` or ``tox -e coverage -- --cov-report=html``.
You can check the HTML coverage report in the newly created `htmlcov` directory.

Code style
----------

We use `ruff <https://docs.astral.sh/ruff/>`_ along with other tools to format our code.
Please run ``tox -e style`` on your patches before submitting them.
In order to perform a style check and correction at each commit you can use our
`pre-commit <https://pre-commit.com/>`_ configuration with ``pre-commit install``.

Documentation
-------------

The documentation is generated when the tests run:

.. code-block:: bash

    tox -e doc

You can also run sphinx by hand, that should be faster since it avoids the tox environment initialization:

.. code-block:: bash

   sphinx-build doc build/sphinx/html

The generated documentation is located at ``build/sphinx/html``.
