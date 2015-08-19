Defining Schemas
================

JSON Schema
-----------

Ramses supports JSON Schema Draft 3 and Draft 4. You can read the official `JSON Schema documentation here <http://json-schema.org/documentation.html>`_.

.. code-block:: json

    {
        "type": "object",
        "title": "Item schema",
        "$schema": "http://json-schema.org/draft-04/schema",
        (...)
    }

All Ramses-specific properties are prefixed with an underscore.

Showing Fields
--------------

If you've enabled authentication, you can list which fields to return to authenticated users in ``_auth_fields`` and to non-authenticated users in ``_public_fields``.

.. code-block:: json

    {
        (...)
        "_auth_fields": ["id", "name", "description"],
        "_public_fields": ["name"],
        (...)
    }

Nested Documents
----------------

If you use ``Relationship`` fields in your schemas, you can list those fields in ``_nested_relationships``. Your fields will then become nested documents instead of just the ``id``.

.. code-block:: json

    {
        (...)
        "_nested_relationships": ["relationship_field_name"]
        (...)
    }

Custom "user" Model
-------------------

When authentication is enabled, a default "user" model will be created automatically with 4 fields: "username", "email", "groups" and "password". You can extend this default model by defining your own "user" schema and by setting ``_auth_model`` to ``true`` on that schema. You can add any additional fields in addition to those 4 default fields.

.. code-block:: json

    {
        (...)
        "_auth_model": true,
        (...)
    }
