Field validators
================

Ramses allows users to define functions that accept field data and return modified field value, may perform validation or perform other actions related to field.

These functions are called "field validators". They are set up per-field and are called when request comes into application that modifies the field for which validator is set up (when field is present in request JSON).


Usage basics
------------

Field validators are defined in your target project just like event handlers:

.. code-block:: python

    @registry.add
    def lowercase(**kwargs):
        """ Make :new_value: lowercase (and stripped) """
        return (kwargs['new_value'] or '').lower().strip()


To use this field validator, define ``_validators`` attribute in your field definition (next to ``_db_settings``) which should be an array listing names of validators to apply. You can also use ``_backref_validators`` attribute defined the same way to specify validators for backref field. For backref validators to be set up, ``_db_settings`` must contain attributes ``document``, ``type=relationship`` and ``backref_name``.

Field validators should expect following kwargs to be passed:

**new_value**
    New value of of field.

**instance**
    Instance affected by request. Is None when set of items is updated in bulk and when item is created.

**field**
    Instance of nefertari.utils.data.FieldData instance containing data of changed field.

**request**
    Current Pyramid Request instance.

**model**
    Model class affected by request.

**event**
    Underlying event object. Should be used to edit other fields of instance using ``event.set_field_value(field_name, value)``.

Processors are called in order they are listed. Each validator must return processed value which is used a input for next validator if present.


Examples
--------

If we had following validators defined:

.. code-block:: python

    from .my_helpers import get_stories_by_ids

    @registry.add
    def lowercase(**kwargs):
        """ Make :new_value: lowercase (and stripped) """
        return (kwargs['new_value'] or '').lower().strip()

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
                "_validators": ["validate_stories_exist"],
                "_backref_validators": ["lowercase"]
            },
            ...
        }
    }

When connected like above:
    * ``validate_stories_exist`` validator will be run when request changes ``User.stories`` value. The validator will make sure all of story IDs from request exist.
    * ``lowercase`` validator will be run when request changes ``Story.owner`` field. The validator will lowercase new value of the ``Story.owner`` field.

To edit other fields of instance, ``event.set_field_value`` method should be used. E.g. if we have fields ``due_date`` and ``days_left`` and we connect validator defined below to field ``due_date``, we can update ``days_left`` from it:

.. code-block:: python

    from .helpers import parse_data
    from datetime import datetime

    @registry.add
    def calculate_days_left(**kwargs):
        parsed_date = parse_data(kwargs['new_value'])
        days_left = (parsed_date-datetime.now()).days
        event = kwargs['event']
        event.set_field_value('days_left', days_left)
        return kwargs['new_value']
