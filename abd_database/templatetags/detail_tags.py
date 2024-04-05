from django import template

register = template.Library()


@register.simple_tag(name="get_test_type")
def get_test_type(object):
    return object._meta.verbose_name.split(' ')[0].capitalize()


@register.filter
def has_uploaded(cycling_tests, user):
    for cyclingtest in cycling_tests:
        if cyclingtest.cellTest.file.batch.user == user:
            return True
    return False


@register.filter(name='split')
def split(text, delimiter) -> str:
    """
    Splits a given text and returns the parts in a list
    """
    return text.split(delimiter)
