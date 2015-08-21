Relationships
=============


Basics
------

Relationships in Ramses are used to represent One-To-Many(o2m) and One-To-One(o2o) relationships between objects in database.

To set up relationships fields of types ``foreign_key`` and ``relationship`` are used. ``foreign_key`` field is not required when using ``nefertari_mongodb`` engine and is ignored.


For this tutorial we are going to use example of users and stories. In this example we have OneToMany relationships betweed User and Story: One user may have many stories but story has only one owner.
Check the end of the tutorial for a complete example of RAML file and schemas.

Example code is the very minimum needed to explain the subject. We will be referring to the examples along all the tutorial.


relationship
------------

Must be defined on *One* side of OneToOne or OneToMany relationship (``User`` in our example). Relationships are created as OneToMany by default. To create OneToOne relationships, specify ``"uselist": false`` in ``_db_settings`` of this field.


Example of using ``relationship`` field:

.. code-block:: json

    "stories": {
        "_db_settings": {
            "type": "relationship",
            "document": "Story",
            "backref_name": "owner"
        }
    }

**Required params:**

*type*
    String. Just ``relationship``.

*document*
    String. Exact name of model class to which relationship is set up. To find out the name of model use singularized uppercased version of route name. E.g. if we want to set up relationship to objects of ``/stories`` then the ``document`` arg will be ``Story``.

*backref_name*
    String. Name of *back reference* field. This field will be auto-generated on model we set up relationship to and will hold the instance of model we are defining. In our example, field ``Story.owner`` will be generated and it will hold instance of ``User`` model to which story instance belongs. **Use this field to change relationships between objects.**


foreign_key
-----------

Must be defined on *Many* side of OneToMany or on the opposite side from ``relationship`` in OneToOne (``Story`` in our example). This represents a Foreign Key constraint in SQL and is required when using ``nefertari_sqla`` engine.

**Notes:**

    * This field is not required and is ignored when using nefertari_mongodb engine.
    * Name of the ``foreign_key`` field does not depend on relationship params in any way.
    * This field **MUST NOT** be used to change relationships. This field only exists because it is required by SQLAlchemy.


Example of using ``foreign_key`` field:

.. code-block:: json

    "owner_id": {
        "_db_settings": {
            "type": "foreign_key",
            "ref_document": "User",
            "ref_column": "user.username",
            "ref_column_type": "string"
        }
    }

**Required params:**

*type*
    String. Just ``foreign_key``.

*ref_document*
    String. Exact name of model class to which foreign key is set up. To find out the name of model use singularized uppercased version of route name. E.g. if we want to set up foreign key to objects of ``/user`` then the ``ref_document`` arg will be ``User``.

*ref_column*
    String. Dotted name/path to ``ref_document`` model's primary key column. ``ref_column`` is a lowercased name of model we reffer in ``ref_document`` joined by doth with an exact name if ``ref_document`` model's primary key column. In our example this is ``"user.username"``.

**ref_column_type**
    String. Ramses field type of ``ref_document`` model's primary key column specified in ``ref_column`` parameter. In our example this is ``"string"`` because ``User.username`` is ``"type": "string"``.






Complete example
----------------

**example.raml**

.. code-block:: yaml

    #%RAML 0.8
    ---
    title: Example REST API
    documentation:
        - title: Home
          content: |
            Welcome to the example API.
    baseUri: http://{host}:{port}/{version}
    version: v1

    /stories:
        displayName: All stories
        get:
            description: Get all stories
        post:
            description: Create a new story
            body:
                application/json:
                    schema: !include story.json
        /{id}:
            displayName: One story
            get:
                description: Get a particular story

    /users:
        displayName: All users
        get:
            description: Get all users
        post:
            description: Create a new user
            body:
                application/json:
                    schema: !include user.json
        /{username}:
            displayName: One user
            get:
                description: Get a particular user


**user.json**

.. code-block:: json

    {
        "type": "object",
        "title": "User schema",
        "$schema": "http://json-schema.org/draft-04/schema",
        "required": ["username"],
        "properties": {
            "username": {
                "_db_settings": {
                    "type": "string",
                    "primary_key": true
                }
            },
            "stories": {
                "_db_settings": {
                    "type": "relationship",
                    "document": "Story",
                    "backref_name": "owner"
                }
            }
        }
    }


**story.json**

.. code-block:: json

    {
        "type": "object",
        "title": "Story schema",
        "$schema": "http://json-schema.org/draft-04/schema",
        "properties": {
            "id": {
                "_db_settings": {
                    "type": "id_field",
                    "primary_key": true
                }
            },
            "owner_id": {
                "_db_settings": {
                    "type": "foreign_key",
                    "ref_document": "User",
                    "ref_column": "user.username",
                    "ref_column_type": "string"
                }
            }
        }
    }
