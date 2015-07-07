Changelog
=========

* :release:`0.3.1 <2015-07-06>`
* :support:`- backported` Added support for callables in 'default' field argument
* :support:`- backported` Added support for 'onupdate' field argument

* :release:`0.3.0 <2015-06-14>`
* :support:`-` Added python3 support

* :release:`0.2.3 <2015-06-05>`
* :bug:`-` Forward compatibility with nefertari releases

* :release:`0.2.2 <2015-06-03>`
* :bug:`-` Fixed password minimum length support by adding before and after validation processors
* :bug:`-` Fixed race condition in Elasticsearch indexing

* :release:`0.2.1 <2015-05-27>`
* :bug:`-` Fixed limiting fields to be searched
* :bug:`-` Fixed login issue
* :bug:`-` Fixed custom processors

* :release:`0.2.0 <2015-05-18>`
* :feature:`-` Added support for securitySchemes, authentication (Pyramid 'auth ticket') and ACLs
* :support:`-` Added several display options to schemas
* :support:`-` Added unit tests
* :support:`-` Improved docs
* :feature:`-` Add support for processors in schema definition
* :feature:`-` Add support for custom auth model
* :support:`-` ES views now read from ES on update/delete_many

* :release:`0.1.1 <2015-04-21>`
* :bug:`-` Ramses could not be used in an existing Pyramid project

* :release:`0.1.0 <2015-04-08>`
* :support:`-` Initial release!
