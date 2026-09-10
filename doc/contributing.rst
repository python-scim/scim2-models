Contributing
============

Contributions are welcome!

The repository is hosted at
`github.com/python-scim/scim2-models <https://github.com/python-scim/scim2-models>`_.

Discuss
-------

A feature or a bugfix starts with a discussion on the
`bugtracker <https://github.com/python-scim/scim2-models/issues>`_.

Unit tests
----------

Run ``uv run pytest`` before submitting a patch. Run ``uv run tox`` to test every supported
Python version. Everything must pass before a patch can be merged.

The test coverage threshold is 100%. Check it with
``uv run pytest --cov --cov-fail-under=100 --cov-report=html``. The report is written to
``htmlcov``.

Code style
----------

The project uses `ruff <https://docs.astral.sh/ruff/>`_ and other checks through
`prek <https://github.com/j178/prek>`_. Run ``uv run prek run --all-files`` before submitting a
patch. Install the hooks with ``uv run prek install`` to run them before each commit.

Documentation
-------------

Build the documentation with warnings treated as errors:

.. code-block:: bash

   uv run sphinx-build -W --keep-going --builder html doc build/sphinx/html

The generated documentation is located at ``build/sphinx/html``.
