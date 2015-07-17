Getting started
===============

1. Create your project in a virtualenv directory (see the `virtualenv documentation <https://virtualenv.pypa.io>`_ if you've never done that before)

.. code-block:: shell

    $ virtualenv my_project
    $ source my_project/bin/activate
    $ pip install ramses
    $ pcreate -s ramses_starter my_project
    $ cd my_project
    $ pserve local.ini

2. Tada! Start editing api.raml to modify the API and items.json for the schema.

Tutorials
---------

- For a more complete example of a Pyramid project using Ramses, you can take a look at the `Example Project <https://github.com/brandicted/ramses-example>`_.
- Check out the great tutorial written by Chris Hart on Real Python: `Create a REST API in Minutes With Pyramid and Ramses <https://realpython.com/blog/python/create-a-rest-api-in-minutes-with-pyramid-and-ramses/>`_.
- RAML can be used to generate an end-to-end application, check out `this example <https://github.com/jstoiko/raml-javascript-client>`_ using Ramses on the backend and RAML-javascript-client + BackboneJS on the front-end.
