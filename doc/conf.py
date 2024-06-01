import datetime
import os
import sys
from importlib import metadata

sys.path.insert(0, os.path.abspath(".."))
sys.path.insert(0, os.path.abspath("../pydantic_scim2"))

# -- General configuration ------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.graphviz",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinxcontrib.autodoc_pydantic",
    "myst_parser",
]

templates_path = ["_templates"]
master_doc = "index"
project = "pydantic-scim2"
year = datetime.datetime.now().strftime("%Y")
copyright = f"{year}, Yaal Coop"
author = "Yaal Coop"
source_suffix = {
    ".rst": "restructuredtext",
    ".txt": "markdown",
    ".md": "markdown",
}

version = metadata.version("pydantic-scim2")
language = "en"
exclude_patterns = []
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
html_baseurl = "https://pydantic-scim2.readthedocs.io"
html_theme_options = {
    "globaltoc_expand_depth": 3,
    "accent_color": "amber",
    "github_url": "https://github.com/yaal-coop/pydantic-scim2",
    "mastodon_url": "https://toot.aquilenet.fr/@yaal",
    "nav_links": [
        {
            "title": "SCIM",
            "url": "https://simplecloud.info/",
            "children": [
                {
                    "title": "RFC7642 - SCIM: Definitions, Overview, Concepts, and Requirements",
                    "url": "https://tools.ietf.org/html/rfc7642",
                },
                {
                    "title": "RFC7643 - SCIM: Core Schema",
                    "url": "https://tools.ietf.org/html/rfc7643",
                },
                {
                    "title": "RFC7644 - SCIM: Protocol",
                    "url": "https://tools.ietf.org/html/rfc7644",
                },
            ],
        },
        {"title": "PyPI", "url": "https://pypi.org/project/pydantic-scim2"},
    ],
}
html_context = {
    "source_type": "github",
    "source_user": "yaal-coop",
    "source_repo": "pydantic-scim2",
    "source_version": "main",
    "source_docs_path": "/doc/",
}

# -- Options for autodoc_pydantic_settings -------------------------------------------

autodoc_pydantic_model_show_config_summary = False
autodoc_pydantic_model_show_field_summary = False
autodoc_pydantic_model_show_json = False

# -- Options for doctest -------------------------------------------

doctest_global_setup = """
from pydantic_scim2 import *
"""
