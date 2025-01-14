from django import forms
from .models import Tarea, Venta, User

class TareaForm(forms.ModelForm):
    venta = forms.ModelChoiceField(queryset=Venta.objects.all(), label="Venta")
    # usuario = forms.ModelChoiceField(queryset=User.objects.all(), label="Usuario")

    class Meta:
        model = Venta
        # mostrar solo los campos especificados
        fields = ['venta']

class AsignarTareaForm(forms.Form):
    # usuario = forms.ModelChoiceField(queryset=User.objects.all(), label="Selecciona un Usuario")
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        label="Select Users",
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control select2',  # Add CSS class for JavaScript library support
            'style': 'width: 25%;'
        })
    )
    # fecha_asignacion = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'date'}))

