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
    "sphinx.ext.graphviz",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinxcontrib.autodoc_pydantic",
    "sphinx_issues",
    "sphinx_paramlinks",
    "sphinx_togglebutton",
    "myst_parser",
]

templates_path = ["_templates"]
master_doc = "index"
project = "scim2-models"
year = datetime.datetime.now().strftime("%Y")
copyright = f"{year}, Yaal Coop"
author = "Yaal Coop"
source_suffix = {
    ".rst": "restructuredtext",
    ".txt": "markdown",
    ".md": "markdown",
}

version = metadata.version("scim2-models")
language = "en"
pygments_style = "sphinx"
todo_include_todos = True
toctree_collapse = False

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
}

# -- Options for HTML output ----------------------------------------------

html_theme = "shibuya"
# html_static_path = ["_static"]
html_baseurl = "https://scim2-models.readthedocs.io"
html_theme_options = {
    "globaltoc_expand_depth": 3,
    "accent_color": "amber",
    "github_url": "https://github.com/python-scim/scim2-models",
    "mastodon_url": "https://toot.aquilenet.fr/@yaal",
    "nav_links": [
        {"title": "scim2-client", "url": "https://scim2-client.readthedocs.io"},
        {"title": "scim2-tester", "url": "https://scim2-tester.readthedocs.io"},
        {
            "title": "scim2-cli",
            "url": "https://scim2-cli.readthedocs.io",
        },
    ],
}
html_context = {
    "source_type": "github",
    "source_user": "python-scim",
    "source_repo": "scim2-models",
    "source_version": "main",
    "source_docs_path": "/doc/",
}

# -- Options for autodoc_pydantic_settings -------------------------------------------

autodoc_pydantic_model_show_config_summary = False
autodoc_pydantic_model_show_field_summary = False
autodoc_pydantic_model_show_json = False
autodoc_pydantic_model_show_validator_summary = False
autodoc_pydantic_model_show_validator_members = False
autodoc_pydantic_field_show_constraints = False
autodoc_pydantic_field_list_validators = False
autodoc_pydantic_field_doc_policy = "docstring"

# -- Options for doctest -------------------------------------------

doctest_global_setup = """
from scim2_models import *
"""

# -- Options for sphinx-issues -------------------------------------

issues_github_path = "python-scim/scim2-models"
