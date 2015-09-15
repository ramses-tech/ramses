Event Handlers
==============

Ramses supports Nefertari event handlers. The following documentation describes how to define and connect them.


Writing Event Handlers
----------------------

You can write custom functions inside your ``__init__.py`` file, then add the ``@registry.add`` decorator before the functions that you'd like to turn into CRUD event handlers. Ramses CRUD event handlers has the same API as Nefertari CRUD event handlers. Check Nefertari CRUD Events doc for more details on events API.

E.g.

.. code-block:: python

    @registry.add
    def lowercase(event):
        """ This processor lowercases the value of a field """
        value = (event.field.new_value or '').lower().strip()
        event.set_field_value(value)


Connecting Event Handlers
-------------------------

When you define event handlers in your ``__init__.py`` as described above, you can apply them on either a per-model or a per-field basis. If multiple handlers are listed, they are executed in the order in which they are listed. Handlers are defined using the ``_event_handlers`` property. This property is an object, keys of which are called "event tags" and values are lists of handler names. Event tags are constructed of two parts: ``<type>_<action>`` whereby:

**type**
    Is either ``before`` or ``after``, depending on when handler should run - before view method call or after respectively.
**action**
    Exact name of Nefertari view method that processes the request (action).

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
    * **set** - triggers on all the following actions: ``create``, ``update``, ``replace`` and ``update_many``

E.g. This example connects the ``lowercase`` handler to the ``before_set`` event.

.. code-block:: json

    "_event_handlers": {
        "before_set": ["lowercase"]
    }

The ``lowercase`` handler will run before any of the following requests are processed:

    * Collection POST
    * Item PATCH
    * Item PUT
    * Collection PATCH
    * Collection PUT


We will use the following handler to demonstrate how to connect handlers to events. This handler logs ``request``.

.. code-block:: python

    import logging
    log = logging.getLogger(__name__)

    @registry.add
    def log_request(event):
        log.debug(event.view.request)


Before vs After
---------------

``Before`` events should be used to:
    * Transform input
    * Perform validation
    * Apply changes to object that is being affected by the request using the ``event.set_field_value`` method

``After`` events should be used to:
    * Change DB objects which are not affected by the request
    * Perform notifications/logging


Per-model Handlers
------------------

To register handlers on a per-model basis, you can define the ``_event_handlers`` property at the root of your model's JSON schema. For example, if we have a JSON schema for the model ``User`` and we want to log all collection GET requests to the ``User`` model after they were processed (using the ``log_request`` handler), we can register the handler in the JSON schema like this:

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


Per-field Handlers
------------------

To register handlers on a per-field basis, you can define the ``_event_handlers`` property inside the fields of your JSON schema (same level as ``_db_settings``).

E.g. if our model ``User`` has a field ``username``, we might want to make sure that ``username`` is not a reserved name. If ``username`` is a reserved name, we want to raise an exception to interrupt the request.

.. code-block:: python

    @registry.add
    def check_username(event):
        reserved = ('admin', 'cat', 'system')
        username = event.field.new_value
        if username in reserved:
            raise ValueError('Reserved username: {}'.format(username))


The following JSON schema registers ``before_set`` on the field ``User.username``. When connected this way, the ``check_username`` handler will only be executed if the request has the field ``username`` passed to it:

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

You can update another field's value, for example, increment a counter:

.. code-block:: python

    @registry.add
    def increment_count(event):
        counter = event.instance.counter
        incremented = counter + 1
        event.set_field_value(incremented, 'counter')


You can transform the value of a field, for example, encrypt a password before saving it:

.. code-block:: python

    @registry.add
    def encrypt(event):
        import cryptacular.bcrypt
        crypt = cryptacular.bcrypt.BCRYPTPasswordManager()
        password = event.field.new_value

        if password and not crypt.match(password):
            encrypted = str(crypt.encode(password))
            event.set_field_value(encrypted)


You can update other collections (or filtered collections), for example, mark sub-tasks as completed whenever a task is completed:

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


You can perform more complex queries using ElasticSearch:

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
