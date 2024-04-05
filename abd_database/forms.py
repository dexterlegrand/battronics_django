import datetime
from datetime import date

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.forms import modelformset_factory
from django.views.generic import TemplateView

from .models import Battery, CellTest, UploadBatch, Supplier, ChemicalType, CylinderFormat, PrismaFormat, Dataset
from django.apps import apps
import queue_settings
from django.utils.translation import gettext_lazy as _


def dynamic_query_by_pk(model_name, primarykey):
    model = apps.get_model('abd_database', model_name)
    try:
        return model.objects.get(pk=primarykey)
    except model.DoesNotExist:
        return model.objects.none()


def file_size(file):
    current_size = 0
    current_size += file.size
    if current_size/1000/1000 > queue_settings.max_batch_size:
        raise forms.ValidationError("Selected files are too large.")


class ContentTypeChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.name.split(' ')[0].capitalize()


class FormatChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        if obj.name == "UNKNOWN":
            return f"UNKNOWN {obj.format_type}"
        return super().label_from_instance(obj)


class NewBatteryForm(forms.ModelForm):
    supplier = forms.ModelChoiceField(queryset=Supplier.objects.all())
    specific_type = forms.CharField()
    theoretical_capacity = forms.FloatField()
    chemical_type_cathode = forms.ModelChoiceField(queryset=ChemicalType.objects.all())
    cathode_proportions = forms.CharField(required=False)
    battery_type = ContentTypeChoiceField(queryset=ContentType.objects.filter(model__in=('prismaformat', 'cylinderformat')))
    cylinder_type = FormatChoiceField(queryset=CylinderFormat.objects.all(), required=False, label="Cylinder Type*")
    prisma_type = FormatChoiceField(queryset=PrismaFormat.objects.all(), required=False, label="Prisma Type*")
    anode_prop = forms.CharField(required=False)
    year = forms.TypedChoiceField(coerce=int, choices=[(r, r) for r in reversed(range(2010, datetime.date.today().year+1))])

    field_order = [
        'supplier', 'specific_type', 'year', 'theoretical_capacity', 'chemical_type_cathode', 'cathode_proportions',
        'battery_type', 'cylinder_type', 'prisma_type', 'chemical_type_anode', 'anode_prop', 'weight',
        'vnom', 'vmax', 'vmin', 'comments'
    ]

    class Meta:
        model = Battery
        exclude = ['battery_type', 'anode_proportions', 'prod_year']
        widgets = {'comments': forms.Textarea()}
        help_texts = {
            'weight': "[g]",
            'vnom': "[V]",
            'vmax': "[V]",
            'vmin': "[V]",
        }
        labels = {
            'vnom': _("Nominal Voltage"),
            'vmax': _("Maximal Voltage"),
            'vmin': _("Minimal Voltage"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['theoretical_capacity'].help_text = "[Ah]"
        self.fields['specific_type'].help_text = "Product identifier"
        self.fields['anode_prop'].help_text = "Relations between the chemicals e.g. x:y:z"
        self.fields['anode_prop'].label = "Anode proportions"
        self.fields['year'].label = "Production Year"
        self.fields['cathode_proportions'].help_text = "Relations between the chemicals e.g. x:y:z"

    def clean(self):
        cleaned_data = super().clean()
        cylinder_type = cleaned_data.get('cylinder_type')
        prisma_type = cleaned_data.get('prisma_type')

        if not cylinder_type and not prisma_type:
            raise forms.ValidationError('Either Cylinder type or Prisma type is required.')
        elif cylinder_type and prisma_type:
            raise forms.ValidationError('Only one of Cylinder type or Prisma type can be filled out.')

        return cleaned_data


class RegisterDataset(forms.ModelForm):
    view_permission = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'User ID'}))

    class Meta:
        model = Dataset
        exclude = ['owner']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


# TODO: check if still used, otherwise remove
class RegisterBatteryForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        object_id = cleaned_data.get("object_id")
        content_type = cleaned_data.get("content_type")
        result = dynamic_query_by_pk(content_type.model, object_id)
        if result:
            return cleaned_data
        else:
            raise forms.ValidationError(
                "There is no entry in '{}' with the ID '{}'".format(content_type.name, object_id)
            )

    class Meta:
        model = Battery
        # fields = ['format', 'type', 'manufacturing_date']
        exclude = ['id']
        # 'barcode', 'barcode_image'

        # widgets = {'manufacturing_date': forms.DateInput(attrs={'type': 'date'}), }


class UploadDataForm(forms.Form):
    file_field = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': 'True', 'accept': '.h5', 'required': 'True'}), validators=[file_size])


class DateInput(forms.DateInput):
    input_type = 'date'


class UploadNewTestsForm(forms.ModelForm):
    file_field = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': 'True', 'required': 'True'}), label="Test File")
    # TODO: set initial value like dataset selection to none --> currently fix value "UNKNOWN"
    extractor = forms.ChoiceField(required=True, choices=[('default', 'Please select a value')] + [(choice.label, choice.value) for choice in UploadBatch.ExtractorTypes if choice.value != 'Unknown'], help_text="Please select the corresponding Extractor to the filetype")

    def __init__(self,  *args, **kwargs):
        """Provide default initial values"""
        initial = kwargs.get('initial', {})
        initial['date'] = date.today()
        kwargs['initial'] = initial
        super(UploadNewTestsForm, self).__init__(*args, **kwargs)
        self.fields['dataset'].queryset = self.fields['dataset'].queryset.exclude(pk=1)

    class Meta:
        model = CellTest
        fields = ['equipment', 'date', 'dataset']
        widgets = {
            'date': forms.HiddenInput(),
        }
        labels = {
            'date': _("First Measure Date"),
        }
        help_texts = {
            'date': "Only needed if in the data the timestamps aren't in a correct form. Please select earliest test date!",
            'dataset': "Select the correct dataset source",
            'equipment': "What equipment did you use to measure the test?",
            # 'extractor': "Please select the corresponding Extractor to the filetype"
        }

    field_order = ['dataset', 'equipment', 'extractor', 'file_field', 'date']


UploadTestFormSet = modelformset_factory(
    CellTest,
    fields=('equipment', 'date', 'dataset'),
    extra=1, min_num=1)


class MyUploadTestFormSet(TemplateView):
    def get(self, request, *args, **kwargs):
        formset = UploadTestFormSet(queryset=CellTest.objects.none())
        return self.render_to_response({'upload_formset': formset})


class TestFormSet(modelformset_factory(CellTest, form=UploadNewTestsForm, extra=1)):
    def __init__(self, *args, **kwargs):
        super(TestFormSet, self).__init__(*args, **kwargs)
        # custom behavior here