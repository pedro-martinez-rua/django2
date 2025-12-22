from django.shortcuts import render
from django.urls import reverse_lazy
from . import models
from django.views import generic
from django.contrib.messages.views import SuccessMessageMixin
from django.core.mail import send_mail
import logging

# Logger for email errors
logger = logging.getLogger(__name__)

def index(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'about.html')

def destinations(request):
    all_destinations = models.Destination.objects.all()
    return render(request, 'destinations.html', {'destinations': all_destinations})

class DestinationDetailView(generic.DetailView):
    template_name = 'destination_detail.html'
    model = models.Destination
    context_object_name = 'destination'

class DestinationCreateView(generic.CreateView):
    model = models.Destination
    template_name = 'destination_form.html'
    fields = ['name', 'description', 'image']

class DestinationUpdateView(generic.UpdateView):
    model = models.Destination
    template_name = 'destination_form.html'
    fields = ['name', 'description', 'image']

class DestinationDeleteView(generic.DeleteView):
    model = models.Destination
    template_name = 'destination_confirm_delete.html'
    success_url = reverse_lazy('destinations')

class CruiseDetailView(generic.DetailView):
    template_name = 'cruise_detail.html'
    model = models.Cruise
    context_object_name = 'cruise'

class InfoRequestCreate(SuccessMessageMixin, generic.CreateView):
    template_name = 'info_request_create.html'
    model = models.InfoRequest
    fields = ['name', 'email', 'cruise', 'notes']
    success_url = reverse_lazy('index')
    success_message = 'Thank you, %(name)s! We will email you when we have more information about %(cruise)s!'

    def form_valid(self, form):
        try:
            # Email to company
            send_mail(
                "New information request",
                f"Name: {form.cleaned_data['name']}\n"
                f"Email: {form.cleaned_data['email']}\n"
                f"Cruise: {form.cleaned_data['cruise']}\n"
                f"Notes: {form.cleaned_data['notes']}",
                "alvaro.pruebasDjango@gmail.com",
                ["alvaro.pruebasDjango@gmail.com"],
            )

            # Confirmation email to user
            send_mail(
                "Request received",
                f"Hello {form.cleaned_data['name']},\n\n"
                "We have received your request for information about "
                f"{form.cleaned_data['cruise']}. We will contact you shortly.\n\n"
                "Thank you!",
                "alvaro.pruebasDjango@gmail.com",
                [form.cleaned_data['email']],
            )
        except Exception as e:
            logger.error(f"Error sending email: {e}")

        return super().form_valid(form)

