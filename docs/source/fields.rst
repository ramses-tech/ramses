Field Types
===========

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

You can use an ``id_field`` in lieu of primary key.

.. code-block:: json

    "id": {
        (...)
        "type": "id_field",
        "args": {
            "primary_key": true
        }
    }

You can alternatively elect a field to be the primary key of your model by setting its ``primary_key`` property under ``args``. For example, if you decide to use ``username`` as the primary key of your `User` model. This will enable resources to refer to that field in their url, e.g. ``/api/users/john``

.. code-block:: json

    "username": {
        (...)
        "type": "string",
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

.. _field-processors:

Field Processors
----------------

Field processors are custom functions that are called upon validation of a field. You can write those functions inside your ``__init__.py``. You can reference processors in the ``before_validation`` and ``after_validation`` properties under ``args``. The `before_` and `after_` prefixes refer to when those processors are executed, either before or after database validation. You can define more than one processor in each of those arguments in a comma-separated list. If multiple processors are listed, they are executed in the order in which they are listed.

.. code-block:: json

    "password": {
        (...)
        "args": {
            "before_validation": ["validate_password_format", "crypt"],
            "after_validation": ["email_password_changed"]
        }
    }

For 'relationship' fields, you can also add processors to your backref field by adding the ``backref_`` prefix.

.. code-block:: json

    "parents": {
        (...)
        "type": "relationship",
        "args": {
            "document": "Parent",
            "backref_name": "child",
            "backref_before_validation": ["verify_filiation"],
            "backref_after_validation": ["copy_parents_lastname"]
        }
    }

To learn more about writing custom processors, see the :ref:`Writing Processors documentation<writing-processors>`.


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

You can set an update default value for your field by setting the ``onupdate`` property under ``args``. This is particularly useful to update 'datetime' fields on every updates, e.g.

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
