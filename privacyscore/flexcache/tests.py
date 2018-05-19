from django.test import TestCase, RequestFactory

from . import FragmentType, get_placeholder_token, build_content_fragments, render_content_fragments


class TestBuildContentFragments(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_build(self):
        request = self.factory.get('/foo')
        username_token = get_placeholder_token()
        num_messages_token = get_placeholder_token()
        request.flexcache_placeholders = {
            username_token: 'username',
            num_messages_token: 'num_messages'
        }
        content = 'Hello {}{} you have {} messages.'.format(username_token,
                                                            username_token,
                                                            num_messages_token)
        fragments = build_content_fragments(content, request)
        expected_fragments = [
            (FragmentType.CONTENT, 'Hello '),
            (FragmentType.PLACEHOLDER, 'username'),
            (FragmentType.PLACEHOLDER, 'username'),
            (FragmentType.CONTENT, ' you have '),
            (FragmentType.PLACEHOLDER, 'num_messages'),
            (FragmentType.CONTENT, ' messages.')
        ]
        self.assertEqual(fragments, expected_fragments)

    def test_build_simple(self):
        request = self.factory.get('/foo')
        content = 'foobar'
        fragments = build_content_fragments(content, request)
        expected_fragments = [(FragmentType.CONTENT, 'foobar')]
        self.assertEqual(fragments, expected_fragments)

    def test_render(self):
        request = self.factory.get('/foo')
        username_token = get_placeholder_token()
        num_messages_token = get_placeholder_token()
        request.flexcache_placeholders = {
            username_token: 'username',
            num_messages_token: 'num_messages'
        }
        content_template = 'Hello {} you have {} messages.'.format(username_token,
                                                                   num_messages_token)
        fragments = build_content_fragments(content_template, request)
        content = render_content_fragments(fragments, {
            'username': 'foobar',
            'num_messages': 42
        }, request)
        expected_content = 'Hello foobar you have 42 messages.'
        self.assertEqual(content, expected_content)
