Fields
======

This is a list of all available types:

* biginteger
* binary
* boolean
* choice
* date
* datetime
* decimal
* dict
* float
* foreign_key (ignored/not required when using mongodb)
* id_field
* integer
* interval
* list
* pickle
* relationship
* smallinteger
* string
* text
* time
* unicode
* unicodetext


Required Fields
---------------

You can set a field as required by setting the ``required`` property under ``_db_settings``.

.. code-block:: json

    "password": {
        (...)
        "_db_settings": {
            (...)
            "required": true
        }
    }


Primary Key
-----------

You can use an ``id_field`` in lieu of primary key.

.. code-block:: json

    "id": {
        (...)
        "_db_settings": {
            (...)
            "primary_key": true
        }
    }

You can alternatively elect a field to be the primary key of your model by setting its ``primary_key`` property under ``_db_settings``. For example, if you decide to use ``username`` as the primary key of your `User` model. This will enable resources to refer to that field in their url, e.g. ``/api/users/john``

.. code-block:: json

    "username": {
        (...)
        "_db_settings": {
            (...)
            "primary_key": true
        }
    }

Constraints
-----------

You can set a minimum and/or maximum length of your field by setting the ``min_length`` / ``max_length`` properties under ``_db_settings``. You can also add a unique constraint on a field by setting the ``unique`` property.

.. code-block:: json

    "field": {
        (...)
        "_db_settings": {
            (...)
            "unique": true,
            "min_length": 5,
            "max_length": 50
        }
    }

.. _field-processors:

Field Processors
----------------

Field processors are custom functions that are called upon validation of a field. You can write those functions inside your ``__init__.py``. You can reference processors in the ``before_validation`` and ``after_validation`` properties under ``_db_settings``. The `before_` and `after_` prefixes refer to when those processors are executed, either before or after database validation. You can define more than one processor in each of those arguments in a comma-separated list. If multiple processors are listed, they are executed in the order in which they are listed.

.. code-block:: json

    "password": {
        (...)
        "_db_settings": {
            (...)
            "before_validation": ["validate_password_format", "crypt"],
            "after_validation": ["email_password_changed"]
        }
    }

For 'relationship' fields, you can also add processors to your backref field by adding the ``backref_`` prefix.

.. code-block:: json

    "parents": {
        (...)
        "_db_settings": {
            "type": "relationship",
            "document": "Parent",
            "backref_name": "child",
            "backref_before_validation": ["verify_filiation"],
            "backref_after_validation": ["copy_parents_lastname"]
        }
    }

To learn more about writing custom processors, see the :ref:`Writing Processors documentation<writing-processors>`.


Relationship Fields
-------------------

You can define the name of your relation model by setting the ``document`` property under ``_db_settings`` in a relationship field. You can also set the ``backref_name`` which will automatically add a field of that name to the relation model.

The example below will create a one-to-one relationship.

.. code-block:: json

    "capital": {
        (...)
        "_db_settings": {
            "type": "relationship",
            "document": "City",
            "backref_name": "country",
            "uselist": false
        }
    }

The example below will create a one-to-many relationship.

.. code-block:: json

    "cities": {
        (...)
        "_db_settings": {
            "type": "relationship",
            "document": "City",
            "backref_name": "country"
        }
    }

The example below will create both relationships above.

.. code-block:: json

    "capital": {
        (...)
        "_db_settings": {
            "type": "relationship",
            "document": "City",
            "uselist": false
        }
    },
    "cities": {
        (...)
        "_db_settings": {
            "type": "relationship",
            "document": "City",
            "backref_name": "country"
        }
    }

Note that when using SQLA, you must add a ``foreign_keys`` property to your relation model in order to have multiple foreign keys pointing to the same model.


Default Value
-------------

You can set a default value for you field by setting the ``default`` property under ``_db_settings``.

.. code-block:: json

    "field": {
        (...)
        "_db_settings": {
            (...)
            "default": "default value"
        }
    },

The ``default`` value can also be set to a Python callable, e.g.

.. code-block:: json

    "datetime_field": {
        (...)
        "_db_settings": {
            (...)
            "default": "{{datetime.datetime.utcnow}}"
        }
    },


Update Default Value
--------------------

You can set an update default value for your field by setting the ``onupdate`` property under ``_db_settings``. This is particularly useful to update 'datetime' fields on every updates, e.g.

.. code-block:: json

    "datetime_field": {
        (...)
        "_db_settings": {
            (...)
            "onupdate": "{{datetime.datetime.utcnow}}"
        }
    },


List Fields
-----------

You can list the accepted values of any ``list`` or ``choice`` fields by setting the ``choices`` property under ``_db_settings``.

.. code-block:: json

    "field": {
        (...)
        "_db_settings": {
            "type": "choice",
            "choices": ["choice1", "choice2", "choice3"],
            "default": "choice1"
        }
    }

You can also provide the list/choice items' ``item_type``.

.. code-block:: json

    "field": {
        (...)
        "_db_settings": {
            "type": "list",
            "item_type": "string"
        }
    }

Other ``_db_settings``
----------------------

Note that you can pass any engine-specific arguments to your fields by defining such arguments in ``_db_settings``.
