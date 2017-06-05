import io
import csv

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.translation import ugettext_lazy as _

from privacyscore.utils import normalize_url
from privacyscore.backend.models import ScanList


class SingleSiteForm(forms.Form):
    url = forms.CharField(label=_('URL'))

    def clean_url(self) -> str:
        url = self.cleaned_data.get('url')
        url = normalize_url(url)

        # TODO: This is not a real validity check
        if '.' not in url:
            raise ValidationError(_('The url is not valid.'))

        return url


class CreateListForm(forms.ModelForm):
    tags = forms.CharField()
    csv_file = forms.FileField(required=False)
    csv_data = forms.CharField(required=False)

    def clean(self):
        csv_file = self.cleaned_data.get('csv_file')
        csv_data = ''
        if csv_file:
            csv_data = csv_file.read().decode('utf-8', errors='replace')
            self.cleaned_data['csv_data'] = csv_data
        elif self.cleaned_data['csv_data']:
            csv_data = self.cleaned_data['csv_data']

        csv_file = io.StringIO(csv_data)

        reader = csv.reader(csv_file, delimiter=';')
        try:
            table_header = next(reader)
        except StopIteration:
            self.add_error('csv_data', forms.ValidationError(_('Invalid CSV header.'), code='invalid_csv_header'))
            return

        try:
            table = []
            for line in reader:
                table.append(line)
        except csv.Error:
            self.add_error('csv_data', ValidationError(_('Invalid CSV data.'), code='invalid_csv'))
            return

        last_index = len(table_header) - 1
        for last_index in range(last_index, 0, -1):
            if table_header[last_index]:
                break
        table_header = table_header[:last_index + 1]
        for i in range(len(table_header)):
            if not table_header[i]:
                table_header[i] = _('Unknown column {}').format(i)
        table_header[0] = _('URL')

        invalid_rows = set()
        num_columns = len(table_header)
        validate_url = URLValidator(schemes=('http', 'https'))
        for i in range(len(table)):
            row = table[i]
            if len(row) > num_columns:
                row = row[:num_columns]
            for j in range(num_columns - len(row)):
                row.append('')
            if row[0] and not row[0].startswith(('http', 'https')):
                row[0] = 'http://' + row[0]
            try:
                validate_url(row[0])
            except ValidationError:
                invalid_rows.add(i)
            table[i] = row

        self._table_header = table_header
        self._table = table
        self._invalid_rows = invalid_rows

    def get_table(self):
        return self._table_header, self._table, self._invalid_rows

    class Meta:
        model = ScanList
        fields = ('name', 'description', 'pseudonym', 'email', 'private')
