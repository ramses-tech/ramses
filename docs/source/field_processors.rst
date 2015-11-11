Field processors
================

Ramses supports `Nefertari field processors <http://nefertari.readthedocs.org/en/stable/field_processors.html>`_. Ramses field processors also have access to `Nefertari's wrapper API <http://nefertari.readthedocs.org/en/stable/models.html#wrapper-api>`_ which provides additional helpers.


Setup
-----

To setup a field processor, you can define the ``_processors`` property in your field definition (same level as ``_db_settings``). It should be an array of processor names to apply. You can also use the ``_backref_processors`` property to specify processors for backref field. For backref processors to work, ``_db_settings`` must contain the following properties: ``document``, ``type=relationship`` and ``backref_name``.

.. code-block:: json

    "username": {
        ...
        "_processors": ["lowercase"]
    },
    ...


You can read more about processors in Nefertari's `field processors documentation <http://nefertari.readthedocs.org/en/stable/field_processors.html>`_ including the `list of keyword arguments <http://nefertari.readthedocs.org/en/stable/field_processors.html#keyword-arguments>`_ passed to processors.


Example
-------

If we had following processors defined:

.. code-block:: python

    from .my_helpers import get_stories_by_ids


    @registry.add
    def lowercase(**kwargs):
        """ Make :new_value: lowercase """
        return (kwargs['new_value'] or '').lower()

    @registry.add
    def validate_stories_exist(**kwargs):
        """ Make sure added stories exist. """
        story_ids = kwargs['new_value']
        if story_ids:
            # Get stories by ids
            stories = get_stories_by_ids(story_ids)
            if not stories or len(stories) < len(story_ids):
                raise Exception("Some of provided stories do not exist")
        return story_ids


.. code-block:: json

    # User model json
    {
        "type": "object",
        "title": "User schema",
        "$schema": "http://json-schema.org/draft-04/schema",
        "properties": {
            "stories": {
                "_db_settings": {
                    "type": "relationship",
                    "document": "Story",
                    "backref_name": "owner"
                },
                "_processors": ["validate_stories_exist"],
                "_backref_processors": ["lowercase"]
            },
            ...
        }
    }

Notes:
    * ``validate_stories_exist`` processor will be run when request changes ``User.stories`` value. The processor will make sure all of story IDs from request exist.
    * ``lowercase`` processor will be run when request changes ``Story.owner`` field. The processor will lowercase new value of the ``Story.owner`` field.
