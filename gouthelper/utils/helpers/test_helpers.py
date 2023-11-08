from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from django.http import HttpResponse  # type: ignore


def tests_print_form_errors(response: Union["HttpResponse", None] = None) -> None:
    """Will print errors for all forms and formsets in the context_data."""
    if response and hasattr(response, "context_data"):
        for key, val in response.context_data.items():
            if key.endswith("_form") or key == "form":
                if getattr(val, "errors", None):
                    print(key, val.errors)
            elif key.endswith("_formset"):
                non_form_errors = val.non_form_errors()
                if non_form_errors:
                    print(key, non_form_errors)
                # Check if the formset has forms and iterate over them if so
                if val.forms:
                    for form in val.forms:
                        if getattr(form, "errors", None):
                            print(key, form.errors)
