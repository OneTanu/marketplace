from django import forms


class ProfileSignupForm(forms.Form):
    first_name = forms.CharField(max_length=150, strip=True, required=True)
    last_name = forms.CharField(max_length=150, strip=True, required=True)

    def signup(self, request, user):
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.save(update_fields=["first_name", "last_name"])
