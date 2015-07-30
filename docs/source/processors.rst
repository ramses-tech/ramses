Field Processors
================

Writing Processors
------------------

You can write custom functions inside your ``__init__.py`` file, then simply add the ``@registry.add`` decorator before the functions that you'd like to turn into processors. A processor receives a number of keyword arguments:

* ``kwargs['instance']`` is the object instance being created or updated
* ``kwargs['new_value']`` is the new value being set
* ``kwargs['field']`` is the name of the field
* ``kwargs['request']`` is the request object which includes the user object `request.user`

E.g.

.. code-block:: python

    @registry.add
    def lowercase(**kwargs):
        """ This processor lowercases the new value of a field """
        return (kwargs['new_value'] or '').lower()

To apply this processor on a field, you can list the name of the method in the ``before_validation`` property of that field's ``args``.

.. code-block:: json

    "field": {
        (...)
        "args": {
            "before_validation": ["lowercase"]
        }
    }

Other things You Can Do
-----------------------

You can update another field's value, for example, increment a counter E.g.

.. code-block:: python

    @registry.add
    def increment_count(**kwargs):

        new_value = kwargs['new_value']
        instance = kwargs['instance']

        instance.counter = instance.counter + 1

        return new_value


You can transform the value of a field, for example, encrypt a password before saving it. E.g.

.. code-block:: python

    @registry.add
    def encrypt(**kwargs):

        import cryptacular.bcrypt
        crypt = cryptacular.bcrypt.BCRYPTPasswordManager()
        new_value = kwargs['new_value']

        if new_value and not crypt.match(new_value):
            new_value = str(crypt.encode(new_value))

        return new_value


You can update other collections (or filtered collections), for example, mark sub-tasks as completed whenever a task is completed. E.g.

.. code-block:: python

    @registry.add
    def mark_subtasks_completed(**kwargs):

        from nefertari import engine
        completed = kwargs['new_value']
        instance = kwargs['instance']

        if completed:
            subtask_model = engine.get_document_cls('Subtask')
            subtasks = subtask_model.get_collection(task_id=instance.id)
            subtask_model._update_many(subtasks, {'completed': True})

        return completed

You can perform more complex queries using ElasticSearch. E.g.

.. code-block:: python

    @registry.add
    def mark_subtasks_after_2015_completed(**kwargs):

        from nefertari import engine
        from nefertari.elasticsearch import ES
        completed = kwargs['new_value']
        instance = kwargs['instance']

        if completed:
            subtask_model = engine.get_document_cls('Subtask')
            subtasks_es = ES(subtask_model.__name__).get_collection(
                    _raw_terms='task_id:{} AND created_at:[2015 TO *]'.format(instance.id))
            subtasks_db = subtask_model.filter_objects(subtasks_es)
            subtask_model._update_many(subtasks_db, {'completed': True})

        return completed
