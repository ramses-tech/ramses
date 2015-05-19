Getting started
===============

**1. Create a Pyramid "starter" project** in a virtualenv directory (see the `pyramid documentation <http://docs.pylonsproject.org/docs/pyramid/en/latest/narr/project.html>`_ if you've never done that before)

.. code-block:: shell

    $ mkvirtualenv MyProject
    $ pip install ramses
    $ pcreate -s starter MyProject
    $ cd MyProject
    $ pip install -e .

Install the database backend of your choice, e.g. sqla or mongodb

.. code-block:: shell

    $ pip install nefertari-<engine>


**2. Add a few settings** to development.ini, inside the ``[app:main]`` section

.. code-block:: ini

    # Elasticsearh settings
    elasticsearch.hosts = localhost:9200
    elasticsearch.sniff = false
    elasticsearch.index_name = myproject
    elasticsearch.index.disable = false

    # path to your RAML file
    ramses.raml_schema = example.raml

    # disable authentication
    ramses.auth = false

    # Set '<nefertari_engine>' (e.g. nefertari_sqla or nefertari_mongodb)
    nefertari.engine = <nefertari_engine>

.. code-block:: ini

    # For sqla:
    sqlalchemy.url = postgresql://localhost:5432/myproject

.. code-block:: ini

    # For mongo:
    mongodb.host = localhost
    mongodb.port = 27017
    mongodb.db = myproject


**3. Replace the file** `myproject/__init__.py`

.. code-block:: python

    from pyramid.config import Configurator


    def main(global_config, **settings):
        config = Configurator(settings=settings)
        config.include('ramses')
        return config.make_wsgi_app()


**4. Create the file** `api.raml`

.. code-block:: yaml

    #%RAML 0.8
    ---
    title: Ramses
    documentation:
        - title: Example REST API
          content: |
            Welcome to the Ramses example API.
    baseUri: http://{host}:{port}/{version}
    version: v1
    mediaType: application/json
    protocols: [HTTP]

    /myitems:
        displayName: Collection of items
        get:
            description: Get all item
        post:
            description: Create a new item
            body:
                application/json:
                    schema: !include items.json

        /{id}:
            displayName: Collection-item
            get:
                description: Get a particular item
            delete:
                description: Delete a particular item
            patch:
                description: Update a particular item


**5. Create the file** `items.json`

.. code-block:: json

    {
        "type": "object",
        "title": "Item schema",
        "$schema": "http://json-schema.org/draft-03/schema",
        "required": true,
        "properties": {
            "id": {
                "required": true,
                "type": "id_field",
                "args": {
                    "primary_key": true
                }
            },
            "name": {
                "required": true,
                "type": "string"
            },
            "description": {
                "required": false,
                "type": "text"
            }
        }
    }


**6. Run your app**

.. code-block:: shell

    $ pserve development.ini
