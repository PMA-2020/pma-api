.. PMA API documentation master file, created by
   sphinx-quickstart on Mon Jul 16 16:03:07 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.
   
   docs:
     rst_language: http://restructuredtext.readthedocs.io/en/latest/sphinx_tutorial.html
     markdown_plugin: https://recommonmark.readthedocs.io/en/latest/auto_structify.html
     sphinx: http://www.sphinx-doc.org/en/master/
     extensions:
       sphinx.ext.autodoc: http://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html
       sphinx.ext.doctest: http://www.sphinx-doc.org/en/master/usage/extensions/doctest.html
       sphinx.ext.coverage: http://www.sphinx-doc.org/en/master/usage/extensions/coverage.html
       sphinxcontrib.httpdomain: https://hoyodecrimen.com/api/ext/httpdomain/doc/index.html
       sphinxcontrib.autohttp.flask: https://sphinxcontrib-httpdomain.readthedocs.io/en/stable/#module-sphinxcontrib.autohttp.flask
       sphinxcontrib.autohttp.flaskqref: https://sphinxcontrib-httpdomain.readthedocs.io/en/stable/#sphinxcontrib-autohttp-flaskqref-quick-api-reference-for-flask-app
       ...Others are also listed below in subsections.
     theme: https://sphinx-rtd-theme.readthedocs.io/en/latest/configuring.html


API Documentation
=================
.. CURRENT SETUP --------------------------------------------------------------
   From http://kartowicz.com/dryobates/2016-10/sphinx-rest-api/
   Can include the following in doctree and it works: pma_api.rst

.. toctree::
   :maxdepth: 1
   :caption: Contents

   content/users/endpoints.md
   content/users/usage.md
   content/developers/for_developers.md


Quick start
-----------

Explore the API at: https://api.pma2020.org/v1/resources

Summary
-------
.. include:: _templates/summary.rst

API Details
-----------
.. include:: _templates/api_details.rst


Indices and tables
==================
* :ref:`genindex`
* :ref:`modindex`


.. SPHINX DEFAULTS ------------------------------------------------------------
.. Sphinx default (start next line with .. to reactivate)
   toctree::
   :maxdepth: 2
   :caption: Contents:

.. From http://kartowicz.com/dryobates/2016-10/sphinx-rest-api/

.. Sphinx default (remove this line to reactivate and trailing ..s to activate)
.. Indices and tables
.. ==================

.. * :ref:`genindex`
.. * :ref:`modindex`
