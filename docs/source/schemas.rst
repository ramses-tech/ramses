Defining Schemas
================

JSON Schema Draft 3
-------------------

Ramses supports JSON Schema Draft 3. You can read the full specifications `here <http://tools.ietf.org/html/draft-zyp-json-schema-03>`_.

.. code-block:: json

    {
        "type": "object",
        "title": "Item schema",
        "$schema": "http://json-schema.org/draft-03/schema",
        "required": true,
        (...)
    }

Showing Fields
--------------

If you've enabled authentication, you can list which fields to return to authenticated users in ``auth_fields`` and to non-authenticated users in ``public_fields``.

.. code-block:: json

    {
        (...)
        "auth_fields": ["id", "name", "description"],
        "public_fields": ["name"],
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

When authentication is enabled, a "user" model will be created automatically with 4 fields: "username", "email", "groups" and "password". You can extend that model by defining your own "user" schema and set ``auth_model`` to ``true`` on that schema.

.. code-block:: json

    {
        (...)
        "auth_model": true,
        (...)
    }

You can define any additional fields you'd like but you'll need to preserve the 4 required fields above.
