import pytest
from mock import Mock, patch

from nefertari.utils import dictset

from .fixtures import engine_mock


class TestSetupTicketPolicy(object):

    def test_no_secret(self, engine_mock):
        from ramses import auth
        with pytest.raises(ValueError) as ex:
            auth._setup_ticket_policy(config='', params={})
        expected = 'Missing required security scheme settings: secret'
        assert expected == str(ex.value)
