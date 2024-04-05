from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy

from abd_database.models import UploadBatch
from jobqueue_manager.manager import add_to_queue


def upload_duplicates(request):
    if request.method == 'POST':
        batch = UploadBatch.objects.get(pk=int(request.POST['batch_id']))
        nbr_of_files = len(batch.uploadfile_set.all())
        add_duplicates_to_queue(request, batch, nbr_of_files)
        return HttpResponseRedirect(reverse_lazy(viewname='abd_db:index', kwargs={'ds': 0}))

def add_duplicates_to_queue(request, batch, nbr_of_files):
    error_message = add_to_queue(batch, request.user)
    if not error_message:
        messages.success(request, f"{nbr_of_files} files added to job queue!")
    else:
        messages.error(request, error_message)
