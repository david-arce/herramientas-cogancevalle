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
    usuario = forms.ModelChoiceField(queryset=User.objects.all(), label="Selecciona un Usuario")
    
    
