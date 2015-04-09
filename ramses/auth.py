"""
Auth module that contains all code needed for authentication/authorization
systems to run.

In particular:
    :AuthUser: Class that is meant to be User class in Auth system.
    :AuthorizationView: View for basic auth operations - login, logout, register.
        Is registered with '/auth' prefix and makes available routes:
        '/auth/login', '/auth/logout', '/auth/register'.
    :includeme: Function that actually creates routes listed above and
        connects view to them.
    :create_admin_user: Function that creates system/admin user.

"""
import logging

import cryptacular.bcrypt
from pyramid.security import authenticated_userid
from pyramid.security import remember, forget

from nefertari import engine as eng
from nefertari.utils import dictset
from nefertari.json_httpexceptions import *
from nefertari.view import BaseView

log = logging.getLogger(__name__)
crypt = cryptacular.bcrypt.BCRYPTPasswordManager()


def lower_strip(value):
    return (value or '').lower().strip()


def crypt_password(password):
    if password:
        password = unicode(crypt.encode(password))
    return password


class AuthUser(eng.BaseDocument):
    __tablename__ = 'authuser'

    id = eng.IdField(primary_key=True)
    username = eng.StringField(
        min_length=1, max_length=50, unique=True,
        required=True, processors=[lower_strip])
    email = eng.StringField(
        unique=True, required=True, processors=[lower_strip])
    password = eng.StringField(
        min_length=3, required=True, processors=[crypt_password])
    group = eng.ChoiceField(
        choices=['admin', 'user'], default='user',
        types_name='auth_user_group_types')

    uid = property(lambda self: str(self.id))

    def verify_password(self, password):
        return crypt.check(self.password, password)

    @classmethod
    def authenticate(cls, params):
        success = False
        user = None
        login = params['login'].lower().strip()

        if '@' in login:
            user = cls.get_resource(email=login)
        else:
            user = cls.get_resource(username=login)

        if user:
            password = params.get('password', None)
            success = (password and user.verify_password(password))
        return success, user

    @classmethod
    def groupfinder(cls, userid, request):
        try:
            user = cls.get_resource(id=userid)
        except JHTTPNotFound:
            forget(request)
        else:
            if user:
                return ['g:%s' % user.group]

    @classmethod
    def create_account(cls, params):
        user_params = dictset(params).subset(
            ['username', 'email', 'password'])
        try:
            return cls.get_or_create(
                email=user_params['email'],
                defaults=user_params)
        except JHTTPBadRequest:
            raise JHTTPBadRequest('Failed to create account.')

    @classmethod
    def get_auth_user(cls, request):
        _id = authenticated_userid(request)
        if _id:
            return cls.get_resource(id=_id)


class AuthorizationView(BaseView):
    _model_class = AuthUser

    def create(self):
        user, created = self._model_class.create_account(self._params)

        if not created:
            raise JHTTPConflict('Looks like you already have an account.')

        return JHTTPOk('Registered')

    def login(self, **params):
        self._params.update(params)
        next = self._params.get('next', '')
        login_url = self.request.route_url('login')
        if next.startswith(login_url):
            next = ''  # never use the login form itself as next

        unauthorized_url = self._params.get('unauthorized', None)
        success, user = self._model_class.authenticate(self._params)

        if success:
            headers = remember(self.request, user.uid)
            if next:
                return JHTTPOk('Logged in', headers=headers)
            else:
                return JHTTPOk('Logged in', headers=headers)
        if user:
            if unauthorized_url:
                return JHTTPUnauthorized(location=unauthorized_url+'?error=1')

            raise JHTTPUnauthorized('Failed to Login.')
        else:
            raise JHTTPNotFound('User not found')

    def logout(self):
        headers = forget(self.request)
        return JHTTPOk('Logged out', headers=headers)


def includeme(config):
    log.info('Connecting auth routes and views')
    config.add_request_method(AuthUser.get_auth_user, 'user', reify=True)
    config.add_route('login', '/login')
    config.add_view(
        view=AuthorizationView,
        route_name='login', attr='login', request_method='POST')

    config.add_route('logout', '/logout')
    config.add_view(
        view=AuthorizationView,
        route_name='logout', attr='logout')

    config.add_route('register', '/register')
    config.add_view(
        view=AuthorizationView,
        route_name='register', attr='create', request_method='POST')

    create_admin_user(config)


def create_admin_user(config):
    log.info('Creating system user')
    settings = config.registry.settings
    try:
        s_user = settings['system.user']
        s_pass = settings['system.password']
        s_email = settings['system.email']
        user, created = AuthUser.get_or_create(
            username=s_user,
            defaults=dict(
                password=s_pass,
                email=s_email,
                group='admin'
            ))
        if created:
            import transaction
            transaction.commit()
    except KeyError as e:
        log.error('Failed to create system user. Missing config: %s' % e)
