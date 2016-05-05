import os
import ra
import webtest
import pytest

appdir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..'))
ramlfile = os.path.abspath(
    os.path.join(os.path.dirname(__file__), 'api.raml'))
testapp = webtest.TestApp('config:local.ini', relative_to=appdir)


@pytest.fixture(autouse=True)
def setup(req, examples):
    """ Setup database state for tests.

    NOTE: For objects to be created, when using SQLA transaction
    needs to be commited as follows:
        import transaction
        transaction.commit()
    """
    from nefertari import engine
    Item = engine.get_document_cls('Item')

    if req.match(exclude='POST /items'):
        if Item.get_collection(_count=True) == 0:
            example = examples.build('item')
            Item(**example).save()


# ra entry point: instantiate the API test suite
api = ra.api(ramlfile, testapp)
api.autotest()
