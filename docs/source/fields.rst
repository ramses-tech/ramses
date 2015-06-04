Field Types
===========

Available Types
---------------

* id_field
* biginteger
* boolean
* date
* datetime
* choice
* float
* integer
* interval
* binary
* decimal
* pickle
* smallinteger
* string
* text
* time
* unicode
* unicodetext
* relationship
* list
* dict

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

You can set a field as the primary key by setting the ``primary_key`` property under ``args``.

.. code-block:: json

    "field": {
        (...)
        "args": {
            "primary_key": true
        }
    }

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

Custom Field Processors
-----------------------

You can set custom field processors by referencing the names of such processors in the ``processors`` property under ``args``.

.. code-block:: json

    "field": {
        (...)
        "args": {
            "processors": ["custom_processor"]
        }
    }

You can then define each custom processor in a function in your ``__init__.py`` file.

.. code-block:: python

    @registry.add
    def custom_processor(value):
        """ This is a field processor """
        return (value or '').lower().strip()

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

You can set a default value to any of your field by setting the ``default`` property under ``args``.

.. code-block:: json

    "field": {
        (...)
        "args": {
            "default": "default value"
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

For ``list`` fields, you can also provide the choice items' ``type``.

.. code-block:: json

    "field": {
        (...)
        "type": "list",
        "args": {
            "choices": ["choice1", "choice2"],
            "default": ["choice1"],
            "item_type": "string"
        }
    }

Other ``args``
--------------

Note that you can pass any engine-specific arguments to your fields by defining such arguments in ``args``.
