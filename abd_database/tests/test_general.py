from django.test import TestCase

from abd_database.models import *
from django.contrib.contenttypes.models import ContentType

class TypeLimitTests(TestCase):

    def test_get_type_limit_for_BatteryFormat(self):
        """
        return selection of allowed types for polymorphism
        """
        # self.assertListEqual(get_type_limit(('prismaisonorm', 'cylinderisonorm')), [Q(app_label='abd_database', model='prismaisonorm'),
        #                           Q(app_label='abd_database', model='cylinderisonorm')])

        # self.assertQuerysetEqual(get_type_limit(('prismaisonorm', 'cylinderisonorm')),
        #                          [Q(app_label='abd_database', model='prismaisonorm'),
        #                           Q(app_label='abd_database', model='cylinderisonorm')]
        #                          )
        self.assertEqual(2, len(ContentType.objects.filter(get_type_limit(('prismaisonorm', 'cylinderisonorm')))))
