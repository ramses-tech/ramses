Getting started
===============

1. Create your project in a virtualenv directory (see the `pyramid documentation <http://docs.pylonsproject.org/docs/pyramid/en/latest/narr/project.html>`_ if you've never done that before)

.. code-block:: shell

    $ virtualenv my_project
    $ source my_project/bin/activate
    $ cd my_project
    $ pip install ramses
    $ pcreate -s ramses_starter my_project
    $ pserve local.ini


2. Tada! Start editing api.raml to modify the API and items.json for the schema.