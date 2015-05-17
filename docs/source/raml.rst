RAML Configuration
==================

You can read the full RAML specs `here <http://raml.org/spec.html>`_.

Authentication
--------------

In order to enable authentication, add the ``ramses.auth`` paramer to your .ini file.

.. code-block:: ini

    ramses.auth = true

In the root section of your RAML file, you can add a ``securitySchemes``, define the ``x_ticket_auth`` method and list it in your root-level ``securedBy``. This will enable cookie-based authentication.

.. code-block:: yaml

    securitySchemes:
        - x_ticket_auth:
            description: Standard Pyramid Auth Ticket policy
            type: x-Ticket
            settings:
                secret: auth_tkt_secret
                hashalg: sha512
                cookie_name: ramses_auth_tkt
                http_only: 'true'
    securedBy: [x_ticket_auth]

A few convenience routes will be automatically added:

* POST ``/auth/register``: register a new user
* POST ``/auth/login``: login an existing user
* GET ``/auth/logout``: logout currently logged-in user

ACLs
----

In your ``securitySchemes``, you can add as many ACLs as you need. Then you can reference these ACLs in your resource's ``securedBy``.

.. code-block:: yaml

    securitySchemes:
        (...)
        - read_only_users:
            description: ACL that allows authenticated users to read
            type: x-ACL
            settings:
                collection: |
                    allow admin all
                    allow authenticated get
                item: |
                    allow admin all
                    allow authenticated get
    (...)
    /items:
        securedBy: [read_only_users]

Enabling HTTP Methods
---------------------

Listing an HTTP method in your resource definition is all it takes to enable such method.

.. code-block:: yaml

    /items:
        (...)
        post:
            description: Create an item
        get:
            description: Get multiple items
        patch:
            description: Update multiple items
        delete:
            description: delete multiple items

        /{id}:
            displayName: One item
            get:
                description: Get a particular item
            delete:
                description: Delete a particular item
            patch:
                description: Update a particular item


You can link your schema definition for each resource by adding it to the ``post`` section.

.. code-block:: yaml

    /items:
        (...)
        post:
            (...)
            body:
                application/json:
                    schema: !include schemas/items.json


