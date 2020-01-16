from django.contrib import admin, messages as notifications
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, reverse, redirect
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property

from . import InputNotInDesiredRangeError


class FormPostHandlerMixin:
    # handle post method for views with FormMixin and ListView/DetailView
    @method_decorator(login_required)
    def post(self, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)


class IntermediateActionMixin:
    model = None
    max_input = 500
    page_title = f"Intermediate Action"
    template_name = "provide_template_name.html"

    def get(self, request):
        if not self.model:
            raise ValueError(f"Provide a model for {self.__class__.__name__}")

        try:
            context = self.get_context_data()
        except self.model.DoesNotExist:
            notifications.error(request, f"Uygun kaynak {self.model._meta.verbose_name_plural} bulunamadı.")
            return redirect(self.get_changelist_url())
        except InputNotInDesiredRangeError:
            notifications.error(request, f"Bir anda en fazla {self.max_input} {self.model._meta.verbose_name} "
                                         f"üzerinde işlem yapabilirsiniz.")
            return redirect(self.get_changelist_url())

        return render(request, self.template_name, context)

    @cached_property
    def object_list(self):
        """
        If you alter the objects in the objects_list in a way that the current get_queryset method won't fetch them
        anymore, cast objest_list in a python list get the former object_list to work on.
        """
        if not self.get_queryset().count():
            raise self.model.DoesNotExist
        return self.get_queryset()

    def get_queryset(self):
        # Filter selected objects
        queryset = self.model.objects.filter(pk__in=self.get_source_ids())
        return queryset

    def get_source_ids(self):
        source_list = self.request.GET.get("source_list", "")

        try:
            source_ids = [int(pk) for pk in source_list.split("-")]
        except (ValueError, OverflowError):
            source_ids = []

        if not source_ids:
            raise self.model.DoesNotExist

        if len(source_ids) > self.max_input:
            raise InputNotInDesiredRangeError

        return source_ids

    def get_context_data(self):
        admin_context = admin.site.each_context(self.request)
        meta = {"title": self.page_title}
        source = {"sources": self.object_list}
        context = {**admin_context, **meta, **source}
        return context

    def get_changelist_url(self):
        return reverse(f"admin:{self.model._meta.app_label}_{self.model.__name__.lower()}_changelist")
