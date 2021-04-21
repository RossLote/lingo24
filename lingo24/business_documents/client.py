import json
import logging
import urlparse

import requests

from .domains import DomainCollection
from .endpoints import API_ENDPOINT_URLS
from .files import FileCollection
from .locales import LocaleCollection
from .services import ServiceCollection
from .projects import ProjectCollection

logger = logging.getLogger('lingo24')


class Client(object):
    def __init__(self, authenticator, endpoint='live', per_page=25):
        self.authenticator = authenticator
        self.endpoint = endpoint
        self.per_page = per_page
        self._api_session = None

    @property
    def api_endpoint_url(self):
        return API_ENDPOINT_URLS[self.endpoint]

    @property
    def status(self):
        data = self.api_get_json('status', authenticate=False)
        return APIStatus(
            version=data['version'],
            date=data['date'],
        )

    @property
    def api_session(self):
        # Using a session for all API communications means that connections
        # can be pooled and reused.
        if self._api_session is None:
            self._api_session = requests.Session()
        return self._api_session

    @property
    def services(self):
        return ServiceCollection(self, per_page=self.per_page)

    @property
    def locales(self):
        return LocaleCollection(self, per_page=self.per_page)

    @property
    def domains(self):
        return DomainCollection(self, per_page=self.per_page)

    @property
    def files(self):
        return FileCollection(self)

    @property
    def projects(self):
        return ProjectCollection(self, per_page=self.per_page)

    def make_url(self, path):
        return urlparse.urljoin(self.api_endpoint_url, path)

    def api_request(self, method, path, authenticate=True, **kwargs):
        headers = kwargs.pop('headers', {})
        url = self.make_url(path)

        def make_request():
            if authenticate:
                auth = 'Bearer {}'.format(self.authenticator.access_token)
                headers.update({'Authorization': auth})
            return self.api_session.request(method, url, headers=headers, **kwargs)

        response = make_request()

        # If the request failed due to the access token being invalid, refresh
        # it and try again.
        if response.status_code == 401:
            self.authenticator.refresh_access_token()
            response = make_request()

        response.raise_for_status()
        request = response.request
        req_headers = request.headers
        req_headers['Authorization'] = '[REMOVED]'

        logger.debug('request.url: {}'.format(request.url))
        logger.debug('request.method: {}'.format(request.method))
        logger.debug('request.headers: {}'.format(req_headers))
        logger.debug('request.body: {}'.format(request.body))
        logger.debug('response.headers: {}'.format(response.headers))
        logger.debug('response.content: {}'.format(response.content))
        logger.debug('response.status_code: {}'.format(response.status_code))

        return response

    def api_get(self, *args, **kwargs):
        return self.api_request('get', *args, **kwargs)

    def api_put(self, *args, **kwargs):
        return self.api_request('put', *args, **kwargs)

    def api_post(self, *args, **kwargs):
        return self.api_request('post', *args, **kwargs)

    def api_delete(self, *args, **kwargs):
        return self.api_request('delete', *args, **kwargs)

    def api_get_json(self, *args, **kwargs):
        headers = kwargs.pop('headers', {})
        headers.update({
            'Accept': 'application/json',
        })
        return self.api_get(headers=headers, *args, **kwargs).json()

    def api_put_json(self, data, *args, **kwargs):
        headers = kwargs.pop('headers', {})
        headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })
        return self.api_put(data=json.dumps(data), headers=headers, *args, **kwargs).json()

    def api_post_json(self, data, *args, **kwargs):
        headers = kwargs.pop('headers', {})
        headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })
        return self.api_post(data=json.dumps(data), headers=headers, *args, **kwargs).json()


class APIStatus(object):
    def __init__(self, version, date):
        self.version = version
        self.date = date

    def __repr__(self):
        return '<APIStatus: v{}>'.format(self.version)
