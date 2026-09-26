from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        choices=[(i, i) for i in range(5, 0, -1)], coerce=int, widget=forms.RadioSelect
    )

    class Meta:
        model = Review
        fields = ["rating", "body", "chemistry", "contains_spoilers"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 4, "placeholder": "What stayed with you? (No spoilers unless you tick the box.)"}),
        }
        labels = {"body": "Your review", "chemistry": "How was your blind date?", "contains_spoilers": "Contains spoilers"}

    def __init__(self, *args, blind_date=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not blind_date:
            del self.fields["chemistry"]
