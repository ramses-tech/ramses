CRUD Events
===========

Ramses supports Nefertari CRUD events. Following documentation describes how to define and connect them.

Writing Processors
------------------

You can write custom functions inside your ``__init__.py`` file, then add the ``@registry.add`` decorator before the functions that you'd like to turn into CRUD event subscriber.
CRUD event subscribers must have the same API as Nefertari CRUD event subscribers. Check Nefertari CRUD Events doc on more details on events API.

E.g.

.. code-block:: python

    @registry.add
    def lowercase(event):
        """ This processor lowercases the value of a field """
        value = (event.field.new_value or '').lower().strip()
        event.set_field_value(value)


Connecting event subscribers
----------------------------

When you defined event subscribers in your ``__init__.py`` as described above, you can connect them per-model or per-modelfield.

In general subscribers are set up using ``_event_handlers`` param. Value of this param is an object, keys of which are so called "event tags" and values are list of subscriber names.
Event tags are constructed of two parts: ``<type>_<action>`` where:

**type**
    Is either ``before`` or ``after``, depending on when subscriber should run - before view method call or after respectively.
**action**
    Exact name of Nefertari view method that processes the request (action)

Complete list of actions:
    * **index** - Collection GET
    * **create** - Collection POST
    * **update_many** - Collection PATCH/PUT
    * **delete_many** - Collection DELETE
    * **collection_options** - Collection OPTIONS
    * **show** - Item GET
    * **update** - Item PATCH
    * **replace** - Item PUT
    * **delete** - Item DELETE
    * **item_options** - Item OPTIONS

And one special action:
    * **set** - includes actions ``create``, ``update``, ``replace``, ``update_many``


E.g. following connects ``lower_strip_processor`` subscriber to ``before_set`` event and the subscriber will run before any of following requests are processed:
    * Collection POST
    * Item PATCH
    * Item PUT
    * Collection PATCH/PUT

.. code-block:: json

    "_event_handlers": {
        "before_set": ["lower_strip_processor"]
    }


We will use following subscriber to demo how to connect subscribers to events. This subscriber logs request.body.

.. code-block:: python

    import logging
    log = logging.getLogger(__name__)

    @registry.add
    def log_request(event):
        log.debug(event.request.body)


Using before/after events
-------------------------

``before`` events should be used to:
    * Transform input
    * Perform validation
    * Apply changes to object that is being affected by request using ``event.set_field_value`` method.

And ``after`` events to:
    * Change DB objects which are not affected by request.
    * Perform notifications/logging.


Per-model subscribers
---------------------

To set up subscribers per-model, define ``_event_handlers`` param at the root of your model's JSON schema. In example if we have JSON schema for model ``User`` and we want to log all collection GET request to ``User`` model after they were processed (using ``log_request`` subscriber), we connect subscriber in json schema like so:


.. code-block:: json

    {
        "type": "object",
        "title": "User schema",
        "$schema": "http://json-schema.org/draft-04/schema",
        "_event_handlers": {
            "after_index": ["log_request"]
        },
        ...
    }

Per-modelfield subscribers
--------------------------

To set up subscribers per-modelfield, define ``_event_handlers`` param in JSON schema of model field you want to set up subscriber for(at the same level with ``_db_settings``).

E.g. if our model ``User`` has fields ``username`` we might want to make sure ``username`` is not a reserved word/name. If ``username`` is a reserved work, we want to raise an exception to interrupt request processing. To do so we define a subscriber:

.. code-block:: python

    @registry.add
    def check_username(event):
        reserved = ('admin', 'cat', 'system')
        username = event.field.new_value
        if username in reserved:
            raise ValueError('Reserved username: {}'.format(username))


Following JSON schema connects ``before_set`` for field ``User.username``. When connected this way, ``check_username`` subscriber will only run before any requests to ``User`` collection which have field ``username`` in request body are processed:

.. code-block:: json

    {
        "type": "object",
        "title": "User schema",
        "$schema": "http://json-schema.org/draft-04/schema",
        "properties": {
            "username": {
                "_db_settings": {...},
                "_event_handlers": {
                    "before_set": ["check_username"]
                }
            }
        }
        ...
    }



Other Things You Can Do
-----------------------

You can update another field's value, for example, increment a counter. E.g. in subscriber connected to item enpoint:

.. code-block:: python

    @registry.add
    def increment_count(event):
        counter = event.instance.counter
        incremented = counter + 1
        event.set_field_value(incremented, 'counter')


You can transform the value of a field, for example, encrypt a password before saving it. E.g. in subscriber that is connected per-field to ``password`` field:

.. code-block:: python

    @registry.add
    def encrypt(event):
        import cryptacular.bcrypt
        crypt = cryptacular.bcrypt.BCRYPTPasswordManager()
        password = event.field.new_value

        if password and not crypt.match(password):
            encrypted = str(crypt.encode(password))
            event.set_field_value(encrypted)


You can update other collections (or filtered collections), for example, mark sub-tasks as completed whenever a task is completed. E.g. in per-field subscriber connected to item endpoint:

.. code-block:: python

    @registry.add
    def mark_subtasks_completed(event):

        from nefertari import engine
        completed = event.field.new_value
        instance = event.instance

        if completed:
            subtask_model = engine.get_document_cls('Subtask')
            subtasks = subtask_model.get_collection(task_id=instance.id)
            subtask_model._update_many(subtasks, {'completed': True})


You can perform more complex queries using ElasticSearch. E.g. in per-field subscriber connected to item endpoint:

.. code-block:: python

    @registry.add
    def mark_subtasks_after_2015_completed(event):

        from nefertari import engine
        from nefertari.elasticsearch import ES
        completed = event.field.new_value
        instance = event.instance

        if completed:
            subtask_model = engine.get_document_cls('Subtask')
            es_query = 'task_id:{} AND created_at:[2015 TO *]'.format(instance.id)
            subtasks_es = ES(subtask_model.__name__).get_collection(_raw_terms=es_query)
            subtasks_db = subtask_model.filter_objects(subtasks_es)
            subtask_model._update_many(subtasks_db, {'completed': True})
