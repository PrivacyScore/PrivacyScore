from django import forms
from django.core.exceptions import ValidationError
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
    class Meta:
        model = ScanList
        fields = ('name', 'description', 'private')