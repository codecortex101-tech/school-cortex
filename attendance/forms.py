from django import forms
from .models import AttendanceSession, AttendanceRecord, AttendanceStatus
from course.models import Course


class AttendanceSessionForm(forms.ModelForm):
    class Meta:
        model = AttendanceSession
        fields = ['course', 'title', 'date', 'start_time', 'end_time', 'session', 'semester']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'course': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Chapter 1 - Introduction'}),
            'session': forms.Select(attrs={'class': 'form-control'}),
            'semester': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        lecturer = kwargs.pop('lecturer', None)
        super().__init__(*args, **kwargs)
        if lecturer:
            self.fields['course'].queryset = Course.objects.filter(
                allocated_course__lecturer=lecturer
            )


class BulkAttendanceForm(forms.Form):
    """Form for marking attendance for all students in a session"""
    
    def __init__(self, *args, **kwargs):
        students = kwargs.pop('students', [])
        super().__init__(*args, **kwargs)
        
        for student in students:
            self.fields[f'status_{student.id}'] = forms.ChoiceField(
                choices=AttendanceStatus.choices,
                widget=forms.Select(attrs={'class': 'form-control status-select'}),
                required=True,
                label=student.get_full_name
            )
            self.fields[f'remarks_{student.id}'] = forms.CharField(
                widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Optional remarks'}),
                required=False,
                label='Remarks'
            )


class DateRangeForm(forms.Form):
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
