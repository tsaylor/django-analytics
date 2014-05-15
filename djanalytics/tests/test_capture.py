import json

from django.test import TestCase
from django.core.urlresolvers import reverse
from djanalytics import models


class TestCapture(TestCase):

    def setUp(self):
        super(TestCapture, self).setUp()
        self.dja_client = models.Client.objects.create(
            name='testclient'
        )
        models.Domain.objects.create(
            pattern='djanalytics.example.com',
            client=self.dja_client
        )

    def test_capture_post(self):
        # first request
        response = self.client.post(
            '%s?dja_id=%s' % (
                reverse('dja_capture', urlconf='djanalytics.urls'),
                self.dja_client.uuid
            ),
            HTTP_USER_AGENT='Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:29.0) '
                            'Gecko/20100101 Firefox/29.0',
            HTTP_REFERER='http://djanalytics.example.com',
            data={
                'qs': 'query_key=query_value&another_query_key=another_query_value',
                'pth': '/'
            }
        )
        self.assertEqual(201, response.status_code)
        data = json.loads(response.content)
        tracking_id = response.client.session['dja_tracking_id']
        tracking_user_id = response.cookies.get('dja_uuid').value
        event = models.RequestEvent.objects.get(
            tracking_key=tracking_id,
            tracking_user_id=tracking_user_id)
        self.assertEqual(
            event.query_string,
            'query_key=query_value&another_query_key=another_query_value'
        )
        self.assertEqual(event.path, '/')
        self.assertEqual(data['dja_tracking_id'], event.tracking_key)
        self.assertEqual(data['dja_uuid'], event.tracking_user_id)

        # second request should have same tracking_id and tracking_user_id
        response = self.client.post(
            '%s?dja_id=%s' % (
                reverse('dja_capture', urlconf='djanalytics.urls'),
                self.dja_client.uuid
            ),
            HTTP_USER_AGENT='Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:29.0) '
                            'Gecko/20100101 Firefox/29.0',
            HTTP_REFERER='http://djanalytics.example.com',
            data={
                'qs': 'query_key=query_value&another_query_key=another_query_value',
                'pth': '/'
            }
        )
        self.assertEqual(202, response.status_code)
        data = json.loads(response.content)
        self.assertEqual(
            models.RequestEvent.objects.filter(
                tracking_key=tracking_id,
                tracking_user_id=tracking_user_id
            ).count(),
            2
        )
        self.assertEqual(data['dja_tracking_id'], event.tracking_key)
        self.assertEqual(data['dja_uuid'], event.tracking_user_id)

        # terminating session
        self.client.cookies.pop('sessionid')
        # third request should still have same tracking_user_id
        response = self.client.post(
            '%s?dja_id=%s' % (
                reverse('dja_capture', urlconf='djanalytics.urls'),
                self.dja_client.uuid
            ),
            HTTP_USER_AGENT='Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:29.0) '
                            'Gecko/20100101 Firefox/29.0',
            HTTP_REFERER='http://djanalytics.example.com',
            data={
                'qs': 'query_key=query_value&another_query_key=another_query_value',
                'pth': '/'
            }
        )
        data = json.loads(response.content)
        self.assertEqual(202, response.status_code)
        self.assertEqual(
            models.RequestEvent.objects.filter(
                tracking_user_id=tracking_user_id
            ).count(),
            3
        )
        self.assertNotEqual(data['dja_tracking_id'], event.tracking_key)
        self.assertEqual(data['dja_uuid'], event.tracking_user_id)

    def test_invalid_client_id(self):
        response = self.client.post(
            '%s?dja_id=%s' % (
                reverse('dja_capture', urlconf='djanalytics.urls'),
                'bogus'
            ),
            HTTP_REFERER='http://djanalytics.example.com',
        )
        self.assertEqual(403, response.status_code)
        self.assertNotIn('dja_tracking_id', response.client.session)
        self.assertEqual('Client not found', response.content)

    def test_invalid_domain_id(self):
        response = self.client.post(
            '%s?dja_id=%s' % (
                reverse('dja_capture', urlconf='djanalytics.urls'),
                self.dja_client.uuid
            ),
            HTTP_REFERER='http://bogus.example.com',
            data={
                'qs': 'query_key=query_value&another_query_key=another_query_value',
                'pth': '/'
            }
        )
        self.assertEqual(403, response.status_code)
        self.assertNotIn('dja_tracking_id', response.client.session)
        self.assertEqual('Invalid domain for client', response.content)

    def test_filtered_ip(self):
        models.IPFilter.objects.create(
            client=self.dja_client,
            netmask='127.0.0.0/24'
        )
        response = self.client.post(
            '%s?dja_id=%s' % (
                reverse('dja_capture', urlconf='djanalytics.urls'),
                self.dja_client.uuid
            ),
            HTTP_USER_AGENT='Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:29.0) '
                            'Gecko/20100101 Firefox/29.0',
            HTTP_REFERER='http://djanalytics.example.com',
            REMOTE_ADDR='127.0.0.1',
            data={
                'qs': 'query_key=query_value&another_query_key=another_query_value',
                'pth': '/'
            }
        )
        self.assertEqual(204, response.status_code)
        self.assertNotIn('dja_tracking_id', response.client.session)

    def test_filtered_path(self):
        models.PathFilter.objects.create(
            client=self.dja_client,
            path_pattern='^/exclude_me/.*'
        )
        response = self.client.post(
            '%s?dja_id=%s' % (
                reverse('dja_capture', urlconf='djanalytics.urls'),
                self.dja_client.uuid
            ),
            HTTP_USER_AGENT='Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:29.0) '
                            'Gecko/20100101 Firefox/29.0',
            HTTP_REFERER='http://djanalytics.example.com',
            REMOTE_ADDR='127.0.0.1',
            data={
                'qs': 'query_key=query_value&another_query_key=another_query_value',
                'pth': '/exclude_me/should_not_report'
            }
        )
        self.assertEqual(204, response.status_code)
        self.assertNotIn('dja_tracking_id', response.client.session)

