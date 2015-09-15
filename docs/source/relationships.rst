Relationships
=============


Basics
------

Relationships in Ramses are used to represent One-To-Many(o2m) and One-To-One(o2o) relationships between objects in database.

To set up relationships fields of types ``foreign_key`` and ``relationship`` are used. ``foreign_key`` field is not required when using ``nefertari_mongodb`` engine and is ignored.


For this tutorial we are going to use the example of users and
stories. In this example we have a OneToMany relationship betweed ``User``
and ``Story``. One user may have many stories but each story has only one
owner.  Check the end of the tutorial for the complete example RAML
file and schemas.

Example code is the very minimum needed to explain the subject. We will be referring to the examples along all the tutorial.


Field "type": "relationship"
----------------------------

Must be defined on the *One* side of OneToOne or OneToMany
relationship (``User`` in our example). Relationships are created as
OneToMany by default.

Example of using ``relationship`` field (defined on ``User`` model in our example):

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


Field "type": "foreign_key"
---------------------------

This represents a Foreign Key constraint in SQL and is only required
when using ``nefertari_sqla`` engine. It is used in conjunction with
the relationship field, but is used on the model that ``relationship``
refers to. For example, if the ``User`` model contained the
``relationship`` field, than the ``Story`` model would need a
``foreign_key`` field.

**Notes:**

    * This field is not required and is ignored when using nefertari_mongodb engine.
    * Name of the ``foreign_key`` field does not depend on relationship params in any way.
    * This field **MUST NOT** be used to change relationships. This field only exists because it is required by SQLAlchemy.


Example of using ``foreign_key`` field (defined on ``Story`` model in our example):

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
    String. Dotted name/path to ``ref_document`` model's primary key
    column. ``ref_column`` is the lowercased name of model we refer to in
    ``ref_document`` joined by a dot with the exact name of its primary key column. In our example this is ``"user.username"``.

**ref_column_type**
    String. Ramses field type of ``ref_document`` model's primary key column specified in ``ref_column`` parameter. In our example this is ``"string"`` because ``User.username`` is ``"type": "string"``.


One to One relationship
-----------------------

To create OneToOne relationships, specify ``"uselist": false`` in ``_db_settings`` of ``relationship`` field. When setting up One-to-One relationship, it doesn't matter which side defines the ``relationship`` field.

E.g. if we had ``Profile`` model and we wanted to set up One-to-One relationship between ``Profile`` and ``User``, we would have to define a regular ``foreign_key`` field on ``Profile``:

.. code-block:: json

    "user_id": {
        "_db_settings": {
            "type": "foreign_key",
            "ref_document": "User",
            "ref_column": "user.username",
            "ref_column_type": "string"
        }
    }

and ``relationship`` field with ``"uselist": false`` on ``User``:

.. code-block:: json

    "profile": {
        "_db_settings": {
            "type": "relationship",
            "document": "Profile",
            "backref_name": "user",
            "uselist": false
        }
    }


This relationship could also be defined the other way but with the same result: ``foreign_key`` field on ``User`` and ``relationship`` field on ``Profile`` pointing to ``User``.


Multiple relationships
----------------------

**Note: This part is only valid(required) for nefertari_sqla engine, as nefertari_mongodb engine does not use foreign_key fields.**

If we were to define multiple relationships from model A to model B,
each relationship must have a corresponding ``foreign_key``
defined. Also you must use a ``foreign_keys`` parameter on each
``relationship`` field to specify which ``foreign_key`` each
``relationship`` uses.

E.g. if we were to add new relationship field ``User.assigned_stories``, relationship fields on ``User`` would have to be defined like this:

.. code-block:: json

    "stories": {
        "_db_settings": {
            "type": "relationship",
            "document": "Story",
            "backref_name": "owner",
            "foreign_keys": "Story.owner_id"
        }
    },
    "assigned_stories": {
        "_db_settings": {
            "type": "relationship",
            "document": "Story",
            "backref_name": "assignee",
            "foreign_keys": "Story.assignee_id"
        }
    }

And fields on ``Story`` like so:

.. code-block:: json

    "owner_id": {
        "_db_settings": {
            "type": "foreign_key",
            "ref_document": "User",
            "ref_column": "user.username",
            "ref_column_type": "string"
        }
    },
    "assignee_id": {
        "_db_settings": {
            "type": "foreign_key",
            "ref_document": "User",
            "ref_column": "user.username",
            "ref_column_type": "string"
        }
    }


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
