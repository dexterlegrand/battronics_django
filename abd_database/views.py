import logging
from datetime import date

from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import generic, View
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.views.generic import FormView, CreateView
from django.http import JsonResponse
from django.http import HttpResponseRedirect

from abd_management.models import User
from jobqueue_manager.manager import add_to_queue, get_queue_status
from .forms import UploadDataForm, UploadNewTestsForm, MyUploadTestFormSet, UploadTestFormSet, \
    TestFormSet, NewBatteryForm, RegisterDataset
from .helpers.modelHelper import save_files
from .helpers.upload import add_duplicates_to_queue
from .models import Battery, CyclingTest, EISTest, AggData, BatteryType, CyclingRawData, UploadBatch, UploadFile, \
    Dataset, CellTest, Proportion, Supplier

logger = logging.getLogger(__name__)


class BatteryTypeView(generic.ListView):
    model = BatteryType
    template_name = "abd_database/battery_type.html"
    context_object_name = "battery_type_list"

    def get_queryset(self):

        battery_list = Battery.objects.all() # filtering solved by RLS

        temp_id = None
        battery_type_dict = []
        for battery in battery_list.order_by('battery_type_id', 'id'):
            if battery.battery_type.id != temp_id:
                temp_id = battery.battery_type.id
                # create a new dict for each battery type
                battery_type_dict.append({
                    'id': battery.battery_type.id,
                    'supplier': battery.battery_type.supplier,
                    'specific_type': battery.battery_type.specific_type,
                    'theoretical_capacity': battery.battery_type.theoretical_capacity,
                    'chemical_type_cathode': battery.battery_type.chemical_type_cathode,
                    'cathode_proportions': battery.battery_type.cathode_proportions,
                    'content_object': battery.battery_type.content_object,
                    'battery_set': [{
                        'id': battery.id,
                        'name': battery.name,
                        'prod_year': battery.prod_year,
                        'chemical_type_anode': battery.chemical_type_anode,
                        'anode_proportions': battery.anode_proportions,
                        'weight': battery.weight,
                        'vnom': battery.vnom,
                        'vmax': battery.vmax,
                        'vmin': battery.vmin,
                        'cell_test': battery.cell_test.all(),
                        'comments': battery.comments
                    }]
                })
            else:
                # append the battery to the existing dict
                battery_type_dict[-1]['battery_set'].append({
                    'id': battery.id,
                    'name': battery.name,
                    'prod_year': battery.prod_year,
                    'chemical_type_anode': battery.chemical_type_anode,
                    'anode_proportions': battery.anode_proportions,
                    'weight': battery.weight,
                    'vnom': battery.vnom,
                    'vmax': battery.vmax,
                    'vmin': battery.vmin,
                    'cell_test': battery.cell_test.all(),
                    'comments': battery.comments
                })

        return battery_type_dict


class BatteryView(generic.ListView):
    model = Battery
    template_name = "abd_database/index.html"
    context_object_name = "battery_list"

    def get_queryset(self, **kwargs):
        dataset_pk = self.kwargs['ds']
        return Battery.objects.all()

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)

        if self.kwargs['ds'] == 0:
            context['dataset'] = 'All'
            print(context)
        else:
            context['dataset'] = Dataset.objects.get(pk=self.kwargs['ds']).name

        return context


class BatteryDetail(FormView):
    model = Battery
    template_name = 'abd_database/battery_details.html'
    form_class = MyUploadTestFormSet
    formset = TestFormSet

    def get(self, request, pk):
        context = {}
        battery = self.model.objects.get(pk=pk)
        context['battery'] = battery
        context['has_tests'] = battery.cell_test.exists()
        context['cycling_tests'] = CyclingTest.objects.get_cycling_tests_for_battery(battery)
        if context['cycling_tests']:
            context['graph'] = CyclingTest.objects.plot_cycles(context['cycling_tests'][0])
        context['upload_test_formset'] = self.formset(queryset=CellTest.objects.none())
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        context['form'] = form
        print('graph', context['graph'])
        return render(request, self.template_name, context)

    def post(self, *args, **kwargs):
        if self.request.method == "POST":
            if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
                tab = self.request.POST['tab']
                if tab == "cycles-tab":
                    test_pk = int(self.request.POST['selection'])
                    graph = CyclingTest.objects.plot_cycles(CyclingTest.objects.get(pk=test_pk), as_dict=True)
                    return JsonResponse({'graph': graph}, status=200)
                elif tab == "capacity-tab":
                    data = {}
                    agg_data = AggData.objects.get_agg_data_for_battery(self.request.POST['battery_pk'])
                    if not agg_data:
                        return JsonResponse({'error': ""}, status=400)
                    data['agg_data'] = agg_data  # list(agg_data.values())
                    if len(self.request.POST.getlist("selected_cycles[]")) == 0:
                        cycles = [agg_data[0][0]]
                    else:
                        cycles = list(map(int, self.request.POST.getlist("selected_cycles[]")))
                    data['graph'] = CyclingRawData.objects.capacity_vs_voltage_for_cycles(cycles=cycles, as_dict=True)
                    return JsonResponse(data, status=200)
                return JsonResponse({'error': ""}, status=400)
            elif self.request.POST['delete-test']:
                form_class = self.get_form_class()
                form = self.get_form(form_class)
                test_pk = int(self.request.POST['delete-test'])
                cell_test = CellTest.objects.get(pk=test_pk)
                cell_test.delete()
                return self.form_valid(form)
        return JsonResponse({"error": ""}, status=400)

    def get_success_url(self):
        return reverse(viewname='abd_db:battery_detail', kwargs={'pk': self.kwargs['pk']})


def cycling_test_detail(request, cycling_test_id):
    cycling_test = get_object_or_404(CyclingTest, pk=cycling_test_id)
    agg_data = AggData.objects.filter(cycling_test=cycling_test)
    return render(request, 'abd_database/cycling_test_details.html',
                  {'cycling_test': cycling_test, 'agg_data': agg_data})


def eis_test_detail(request, eis_test_id):
    eis_test = get_object_or_404(EISTest, pk=eis_test_id)
    return render(request, 'abd_database/eis_test_details.html', {'eis_test': eis_test})


class FileFieldFormView(FormView):
    form_class = UploadDataForm
    template_name = 'abd_database/load_data_files.html'
    success_url = reverse_lazy(viewname='abd_db:index', kwargs={'ds': 0})

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        files = form.files.getlist('file_field')
        if form.is_valid():
            # batch_with_duplicates(Tuple<batch(UploadBatch), duplicates_in_db(list<Tuples<>>), duplicates_in_queue(list<string>)>
            # batch.1.0 -> duplicates_in_db, batch.1.1 -> duplicates_in_queue
            batch_with_duplicates = save_files(files, request.user, "Hdf5Extractor")
            if batch_with_duplicates:
                if not batch_with_duplicates[1][0] and not batch_with_duplicates[1][1]:
                    add_duplicates_to_queue(request, batch_with_duplicates[0], len(files))
                    return HttpResponseRedirect(reverse_lazy(viewname='abd_db:index', kwargs={'ds': 0}))
                else:
                    return render(request, "abd_database/confirm_upload.html", {'batch_with_duplicates': batch_with_duplicates})
            else:
                # TODO: add error handling --> occurs if in save_files returns nothing
                return self.form_invalid(form)
            return self.form_valid(form)
        else:
            return self.form_valid(form)


class RegisterBattery(FormView):
    template_name = "abd_database/register_battery.html"
    form_class = NewBatteryForm

    # TODO: permission to save

    @transaction.atomic
    def form_valid(self, form):
        type_attrs = {
            'supplier': form.cleaned_data['supplier'],
            'specific_type': form.cleaned_data['specific_type'],
            'theoretical_capacity': form.cleaned_data['theoretical_capacity'],
            'chemical_type_cathode': form.cleaned_data['chemical_type_cathode'],
            'cathode_proportions': Proportion.get_or_create(form.cleaned_data['cathode_proportions']),
            'content_type': form.cleaned_data['battery_type']
        }
        if form.cleaned_data['prisma_type']:
            type_attrs.update({'object_id': form.cleaned_data['prisma_type'].pk})
        elif form.cleaned_data['cylinder_type']:
            type_attrs.update({'object_id': form.cleaned_data['cylinder_type'].pk})

        battery_type, created = BatteryType.objects.get_or_create(**type_attrs)

        battery_attrs = {
            'chemical_type_anode': form.cleaned_data['chemical_type_anode'],
            'anode_proportions': Proportion.get_or_create(form.cleaned_data['anode_prop']),
            'battery_type': battery_type,
            'weight': form.cleaned_data['weight'],
            'vnom': form.cleaned_data['vnom'],
            'vmax': form.cleaned_data['vmax'],
            'vmin': form.cleaned_data['vmin'],
            'prod_year': form.cleaned_data['year'],
            'comments': form.cleaned_data['comments'],
            'owner': form.cleaned_data['owner']
        }
        battery = Battery.objects.create(**battery_attrs)
        self.battery = battery
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(viewname='abd_db:battery_detail', kwargs={'pk': self.battery.pk})


class RegisterDataset(FormView):
    template_name = 'abd_database/register_dataset.html'
    form_class = RegisterDataset
    success_url = reverse_lazy(viewname='abd_management:resources')

    def form_valid(self, form):
        form.instance.owner = self.request.user.company

        form.save()
        saved_object = form.instance
        group = Group.objects.get_or_create(name=f'dataset_{saved_object.pk}')[0]
        group.user_set.add(self.request.user)
        group.save()
        if form.cleaned_data['view_permission']:
            if User.objects.filter(id=form.cleaned_data['view_permission']).exists():
                user = User.objects.filter(id=form.cleaned_data['view_permission']).first()
                group.user_set.add(user)
        return super().form_valid(form)


class RegisterSupplier(CreateView):
    model = Supplier
    template_name = 'abd_database/register_supplier.html'
    fields = '__all__'

    def form_valid(self, form):
        # TODO: do not fake successful response, fix 302
        response = super().form_valid(form)
        data = {'success': True}
        return JsonResponse(data)

    def get_success_url(self):
        return reverse_lazy(viewname='abd_db:index', kwargs={'ds': 0})


class JobViewQueue(View):
    template_name = 'abd_database/job_queue.html'
    success_url = reverse_lazy('abd_db:job_queue')

    @staticmethod
    def get_context(request):
        context = {}
        queue_status = get_queue_status(request.user)
        context['job_queue'] = queue_status
        # TODO: add load more button on template to load more than 10 jobs
        # TODO: check for time
        query = Q(user=request.user)
        # query.add(Q(), Q.AND)
        uploaded_batches = UploadBatch.objects.filter(Q(user=request.user)).order_by('-id')[:10]
        uploaded_files = []
        for batch in uploaded_batches:
            uploaded_files.extend(batch.uploadfile_set.all())
        context['uploaded_files'] = uploaded_files
        context['uploaded_batches'] = uploaded_batches
        return context

    def get(self, request):
        context = self.get_context(request)
        return render(request, self.template_name, context)

    def post(self, *args, **kwargs):
        if self.request.method == "POST":
            if 'redo-file' in self.request.POST:
                file_id = int(self.request.POST['redo-file'])
                if file_id:
                    file = UploadFile.objects.get(pk=file_id)
                    file.time = timezone.now()
                    file.set_status(UploadFile.StatusCodes.INITIAL)
                    file.save(update_fields=['time', 'status'])
                    batch = file.batch
                    # TODO: add some logg messages
                    argument_list = (file.battery, None, date.today(), batch.dataset)
                    errors = add_to_queue(batch, self.request.user, argument_list, file_id)
            elif 'redo-batch' in self.request.POST:
                batch_id = int(self.request.POST['redo-batch'])
                if batch_id:
                    batch = UploadBatch.objects.get(pk=batch_id)
                    battery = None
                    for file in batch.uploadfile_set.all().filter(~Q(status='SUCCESS') & Q(forget=False)):
                        file.time = timezone.now()
                        file.set_status(UploadFile.StatusCodes.INITIAL)
                        file.save(update_fields=['time', 'status'])
                        if battery and battery != file.battery:
                            raise Exception("Too many different batteries found")
                        else:
                            battery = file.battery
                    argument_list = (battery, None, date.today(), batch.dataset)
                    errors = add_to_queue(batch, self.request.user, argument_list)
            elif 'reupload-file' in self.request.POST:
                file_id = int(self.request.POST['reupload-file'])
                if file_id:
                    context = {}
                    context["file_id"] = file_id
                    # context["form"] = UploadDataForm()
                    context["form"] = UploadNewTestsForm()
                    return render(self.request, "abd_database/reupload_data_file.html", context)
            elif 'forget-file' in self.request.POST:
                file_id = int(self.request.POST['forget-file'])
                if file_id:
                    file = UploadFile.objects.get(pk=file_id)
                    file.set_forget()

        context = self.get_context(self.request)
        return render(self.request, self.template_name, context)


class Reuploadfile(FormView):
    form_class = UploadNewTestsForm
    success_url = reverse_lazy('abd_db:job_queue')
    template_name = 'abd_database/reupload_data_file.html'

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        origin_file_id = int(kwargs['file_id'])
        uploadfile = UploadFile.objects.get(pk=origin_file_id)
        if form.is_valid():
            files = form.files.getlist('file_field')
            if origin_file_id and uploadfile:
                uploadfile.file = files[0]
                uploadfile.kb = files[0].size / 1000
                uploadfile.time = timezone.now()
                uploadfile.save()

                batch = uploadfile.batch

                equipment = form.cleaned_data['equipment']
                date = form.cleaned_data['date']
                dataset = form.cleaned_data['dataset']

                argument_list = (uploadfile.battery, equipment, date, dataset)
                errors = add_to_queue(batch, self.request.user, argument_list, origin_file_id)

                return self.form_valid(form)
        else:
            return self.form_invalid(form)


@method_decorator(csrf_exempt, name='dispatch')
class ExtendTests(FormView):
    form_class = UploadNewTestsForm
    template_name = 'abd_database/battery_details.html'

    def setup(self, request, *args, **kwargs):
        # remove InMemoryHandler to force it to use TempFileHanlder(saves it in media folder)
        request.upload_handlers.pop(0)
        super(ExtendTests, self).setup(request, *args, **kwargs)

    @method_decorator(csrf_protect)
    def post(self, request, *args, **kwargs):
        battery = Battery.objects.get(pk=self.kwargs['pk'])
        formset = UploadTestFormSet(request.POST, request.FILES, prefix='form')

        if formset.is_valid():
            for form in formset:
                files = form.files.getlist(form.prefix + "-file_field")
                extractor = form.data[form.prefix + "-extractor"]
                if extractor == UploadBatch.ExtractorTypes.UNKNOWN:
                    raise ValueError("Unknown Extractor is not allowed")
                equipment = form.cleaned_data['equipment']
                date = form.cleaned_data['date']
                dataset = form.cleaned_data['dataset']
                batch_with_duplicates = save_files(files, request.user, extractor, battery, dataset)
                # TODO: handle what happens if duplicate is found
                # TODO: error webpage if duplicates are found --> make better
                if len(batch_with_duplicates[1][0]) > 0 or len(batch_with_duplicates[1][1]) > 0:
                    return self.form_invalid(formset)
                argument_list = (battery, equipment, date, dataset)
                add_to_queue(batch_with_duplicates[0], request.user, argument_list)
            return self.form_valid(formset)
        else:
            return self.form_invalid(formset)

    def get_success_url(self):
        return reverse(viewname='abd_db:battery_detail', kwargs={'pk': self.kwargs['pk']})
