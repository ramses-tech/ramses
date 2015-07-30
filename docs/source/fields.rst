Field Types
===========

Available Types
---------------

* biginteger
* binary
* boolean
* choice
* date
* datetime
* decimal
* dict
* float
* foreign_key
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

You can set a field as required by setting the ``required`` property.

.. code-block:: json

    "field": {
        "required": true,
        (...)
    }


Primary Key
-----------

You can elect a field to be the primary key of a model by setting its ``primary_key`` property under ``args``, for example, if you decide to use `username` as the primary key of your `User` model.

.. code-block:: json

    "username": {
        (...)
        "args": {
            "primary_key": true
        }
    }

Note that you do not need to define ``id_field`` for models that have a primary key defined.

Constraints
-----------

You can set a minimum and/or maximum length of your field by setting the ``min_length`` / ``max_length`` properties under ``args``. You can also add a unique constraint on a field by setting the ``unique`` property.

.. code-block:: json

    "field": {
        (...)
        "args": {
            "unique": true,
            "min_length": 5,
            "max_length": 50
        }
    }


Field Processors
----------------

You can define field processors by referencing their names in the ``before_validation`` and ``after_validation`` properties under ``args``. The `before_` and `after_` prefixes refer to when those processors are executed, either before or after database validation. You can define more than one processor in each of those arguments in a comma-separated list.

.. code-block:: json

    "field": {
        (...)
        "args": {
            "before_validation": ["custom_processor"],
            "after_validation": ["other_custom_processor"]
        }
    }

You can read more about writing custom field processors :doc:`here <processors>`.


Relationship Fields
-------------------

For relationship fields, you can define the name of your 'relation' model by setting the ``document`` property under ``args``. You can also set the ``backref_name`` which will automatically add a field of that name to your schema. Note that for SQLA, you must add a ``foreign_keys`` arg to your 'relation' model if you want to use multiple foreign keys pointing to the same model (see nefertari-example).

.. code-block:: json

    "field": {
        (...)
        "type": "relationship",
        "args": {
            "document": "Name_of_relation_model",
            "backref_name": "backref_field_name"
        }
    }


Default Value
-------------

You can set a default value for you field by setting the ``default`` property under ``args``.

.. code-block:: json

    "field": {
        (...)
        "args": {
            "default": "default value"
        }
    },

The ``default`` value can also be set to a Python callable, e.g.

.. code-block:: json

    "datetime_field": {
        (...)
        "args": {
            "default": "{{datetime.datetime.utcnow}}"
        }
    },


Update Default Value
--------------------

You can set an update default value for your field by setting the ``onupdate`` property under ``args``. This is particularly useful to update datetime fields on every updates, e.g.

.. code-block:: json

    "datetime_field": {
        (...)
        "args": {
            "onupdate": "{{datetime.datetime.utcnow}}"
        }
    },


List Fields
-----------

You can list the accepted values of any ``list`` or ``choice`` fields by setting the ``choices`` property under ``args``.

.. code-block:: json

    "field": {
        (...)
        "type": "choice",
        "args": {
            "choices": ["choice1", "choice2", "choice3"],
            "default": "choice1"
        }
    }

You can also provide the list/choice items' ``type``.

.. code-block:: json

    "field": {
        (...)
        "type": "list",
        "args": {
            "item_type": "string"
        }
    }

Other ``args``
--------------

Note that you can pass any engine-specific arguments to your fields by defining such arguments in ``args``.
