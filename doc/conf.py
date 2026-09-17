import datetime
import os
import sys
from importlib import metadata

sys.path.insert(0, os.path.abspath(".."))
sys.path.insert(0, os.path.abspath("../scim2_models"))

# -- General configuration ------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx_issues",
    "sphinx_paramlinks",
    "sphinx_reredirects",
]

templates_path = ["_templates"]
master_doc = "index"
project = "scim2-models"
year = datetime.datetime.now().strftime("%Y")
copyright = f"{year}, Yaal Coop"
author = "Yaal Coop"
source_suffix = {".rst": "restructuredtext"}

version = metadata.version("scim2-models")
language = "en"
pygments_style = "sphinx"
todo_include_todos = False
toctree_collapse = False

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "scim2_client": ("https://scim2-client.readthedocs.io/en/latest/", None),
    "scim2_tester": ("https://scim2-tester.readthedocs.io/en/latest/", None),
    "scim2_cli": ("https://scim2-cli.readthedocs.io/en/latest/", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
    "flask": ("https://flask.palletsprojects.com/en/stable/", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/20/", None),
}

# -- Sibling projects ------------------------------------------------------

# Kept identical in the scim2-models, scim2-client, scim2-cli and scim2-tester
# documentations, so that any divergence shows up in a diff.
NAV_LINKS = [
    {
        "title": "Libraries",
        "children": [
            {
                "title": "scim2-models",
                "url": "https://scim2-models.readthedocs.io",
                "summary": "SCIM resources and messages as Pydantic models",
            },
            {
                "title": "scim2-client",
                "url": "https://scim2-client.readthedocs.io",
                "summary": "Pythonically build SCIM requests and parse SCIM responses",
            },
        ],
    },
    {
        "title": "Tools",
        "children": [
            {
                "title": "scim2-tester",
                "url": "https://scim2-tester.readthedocs.io",
                "summary": "Check a SCIM server for RFC compliance",
            },
            {
                "title": "scim2-cli",
                "url": "https://scim2-cli.readthedocs.io",
                "summary": "Query a SCIM server from the command line",
            },
            {
                "title": "scim2-server",
                "url": "https://github.com/python-scim/scim2-server",
                "summary": "A lightweight SCIM2 server prototype",
            },
            {
                "title": "pytest-scim2-server",
                "url": "https://github.com/pytest-dev/pytest-scim2-server",
                "summary": "A SCIM2 server fixture for pytest",
            },
        ],
    },
    {
        "title": "Integrations",
        "children": [
            {
                "title": "scim2-flask",
                "url": "https://scim2-flask.readthedocs.io",
                "summary": "Painless SCIM integration for Flask",
            },
            {
                "title": "scim2-django",
                "url": "https://scim2-django.readthedocs.io",
                "summary": "Painless SCIM integration for Django",
            },
            {
                "title": "scim2-fastapi",
                "url": "https://scim2-fastapi.readthedocs.io",
                "summary": "Painless SCIM integration for FastAPI",
            },
        ],
    },
]

# -- Options for HTML output ----------------------------------------------

html_theme = "shibuya"
html_baseurl = "https://scim2-models.readthedocs.io"
html_logo = "_static/python-scim.svg"
html_theme_options = {
    "globaltoc_expand_depth": 3,
    "accent_color": "amber",
    "github_url": "https://github.com/python-scim/scim2-models",
    "mastodon_url": "https://toot.aquilenet.fr/@yaal",
    "nav_links": NAV_LINKS,
}
html_context = {
    "source_type": "github",
    "source_user": "python-scim",
    "source_repo": "scim2-models",
    "source_version": "main",
    "source_docs_path": "/doc/",
}

# -- Options for doctest -------------------------------------------

doctest_global_setup = """
from scim2_models import *
"""

# -- Redirections -------------------------------------------------

# The pages the documentation reorganisation moved, so that published links
# and bookmarks keep working.
redirects = {
    "tutorial": "overview.html",
    "filters": "explanation/filters.html",
    "patch": "explanation/patch.html",
    "guides/index": "../integrations/index.html",
    "guides/flask": "../integrations/flask.html",
    "guides/django": "../integrations/django.html",
    "guides/fastapi": "../integrations/fastapi.html",
    "guides/sqlalchemy": "../integrations/sqlalchemy.html",
}

# -- Options for sphinx-issues -------------------------------------

issues_github_path = "python-scim/scim2-models"


# -- Cross-references ----------------------------------------------


def prefer_builtin_type():
    """Let the ``type`` builtin win over the SCIM attributes of the same name.

    :rfc:`RFC7643` gives most multi-valued attributes a ``type`` sub-attribute,
    and those shadow the builtin in the lookup the annotations autodoc renders
    go through: ``type[BaseModel]`` used to link to ``Address.type``. Reporting
    no local match leaves the reference to intersphinx, which answers with the
    builtin.
    """
    # Imported here rather than at the top of the file: pytest collects this
    # module for its doctests, in an environment that has no Sphinx.
    from sphinx.domains.python import PythonDomain

    find_obj = PythonDomain.find_obj

    def prefer_builtin(self, env, modname, classname, name, objtype, searchmode=0):
        matches = find_obj(self, env, modname, classname, name, objtype, searchmode)
        return [] if name == "type" and len(matches) > 1 else matches

    PythonDomain.find_obj = prefer_builtin


# -- Members -------------------------------------------------------


def skip_unwanted_member(app, what, name, obj, skip, options):
    """Leave duplicate aliases and Pydantic implementation details out.

    ``User.Name`` is the ``Name`` model, as ``User.Emails`` is ``Email``.
    autodoc renders the latter as an alias, but takes an attribute named like
    the class it holds for a nested class, and describes ``Name`` a second time
    under ``User``: the same canonical object twice, which the Python domain
    reports as a duplicate description.

    ``model_config`` and ``model_post_init`` respectively expose implementation
    configuration and an inherited Pydantic lifecycle hook. They are not part of
    the SCIM model API documented here.
    """
    if what == "class" and name in {"model_config", "model_post_init"}:
        return True
    if what != "module" and isinstance(obj, type) and obj.__name__ == name:
        return True
    return None


def setup(app):
    """Register the adjustments the reference page needs."""
    prefer_builtin_type()
    app.connect("autodoc-skip-member", skip_unwanted_member)
