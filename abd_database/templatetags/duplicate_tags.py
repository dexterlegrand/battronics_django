from django import template

from abd_database.models import UploadFile

register = template.Library()


@register.simple_tag(name="get_batteries_from_pk")
def get_batteries_from_pk(file, duplicates):
    duplicate_batteries = []
    for duplicate in duplicates:
        if duplicate[0] == file.pk:
            for primarykey in duplicate[1]:
                duplicate_batteries.append(UploadFile.objects.get(pk=primarykey).battery)
    return duplicate_batteries


@register.simple_tag(name="match_file_to_queue_duplicates")
def match_file_to_queue_duplicates(file, duplicates):
    for item in duplicates:
        if item[0] == file.pk:
            return item[1]

    # TODO: handle exception
    raise Exception(f'could not find {file.pk} in duplicates list')
