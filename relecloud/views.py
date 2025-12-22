from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from . import models
from django.views import generic
from django.contrib.messages.views import SuccessMessageMixin
from django.core.mail import send_mail
import logging
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Count
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required

from django.db.models.functions import Coalesce



# Logger for email errors
logger = logging.getLogger(__name__)

def index(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'about.html')

def destinations(request):
    all_destinations = (
        models.Destination.objects
        .annotate(
            review_count=Count("reviews", distinct=True),
            avg_rating=Coalesce(Avg("reviews__rating"), 0.0),
        )
        .order_by("-review_count", "-avg_rating", "name")
    )
    return render(request, 'destinations.html', {'destinations': all_destinations})


class DestinationDetailView(generic.DetailView):
    template_name = 'destination_detail.html'
    model = models.Destination
    context_object_name = 'destination'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        destination = self.object

        ctx["avg_rating"] = destination.reviews.aggregate(a=Avg("rating"))["a"]
        ctx["reviews"] = destination.reviews.select_related("user").order_by("-created_at")

        user = self.request.user
        ctx["can_review"] = user.is_authenticated and models.Purchase.objects.filter(
            user=user,
            cruise__destinations=destination
        ).exists()
        return ctx


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
    
class DestinationReviewCreateUpdateView(LoginRequiredMixin, generic.View):
    def get(self, request, pk):
        destination = get_object_or_404(models.Destination, pk=pk)
        if not models.Purchase.objects.filter(user=request.user, cruise__destinations=destination).exists():
            messages.error(request, "You can only review destinations you have purchased.")
            return redirect("destination_detail", pk=pk)

        existing = models.Review.objects.filter(user=request.user, destination=destination).first()
        return render(request, "review_form.html", {"target": destination, "target_type": "destination", "review": existing})

    def post(self, request, pk):
        destination = get_object_or_404(models.Destination, pk=pk)
        if not models.Purchase.objects.filter(user=request.user, cruise__destinations=destination).exists():
            messages.error(request, "You can only review destinations you have purchased.")
            return redirect("destination_detail", pk=pk)

        rating = int(request.POST.get("rating", "0"))
        comment = request.POST.get("comment", "")

        models.Review.objects.update_or_create(
            user=request.user,
            destination=destination,
            defaults={"rating": rating, "comment": comment},
        )
        messages.success(request, "Review saved.")
        return redirect("destination_detail", pk=pk)

class CruiseDetailView(generic.DetailView):
    template_name = 'cruise_detail.html'
    model = models.Cruise
    context_object_name = 'cruise'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        cruise = self.object

        ctx["avg_rating"] = cruise.reviews.aggregate(a=Avg("rating"))["a"]
        ctx["reviews"] = cruise.reviews.select_related("user").order_by("-created_at")

        user = self.request.user
        has_purchased = user.is_authenticated and models.Purchase.objects.filter(user=user, cruise=cruise).exists()
        ctx["has_purchased"] = has_purchased

        # si en otros templates lo usas, puedes mantener can_review igual:
        ctx["can_review"] = has_purchased
        return ctx

class CruiseReviewCreateUpdateView(LoginRequiredMixin, generic.View):
    def get(self, request, pk):
        cruise = get_object_or_404(models.Cruise, pk=pk)
        if not models.Purchase.objects.filter(user=request.user, cruise=cruise).exists():
            messages.error(request, "You can only review cruises you have purchased.")
            return redirect("cruise_detail", pk=pk)

        existing = models.Review.objects.filter(user=request.user, cruise=cruise).first()
        return render(request, "review_form.html", {"target": cruise, "target_type": "cruise", "review": existing})

    def post(self, request, pk):
        cruise = get_object_or_404(models.Cruise, pk=pk)
        if not models.Purchase.objects.filter(user=request.user, cruise=cruise).exists():
            messages.error(request, "You can only review cruises you have purchased.")
            return redirect("cruise_detail", pk=pk)

        rating = int(request.POST.get("rating", "0"))
        comment = request.POST.get("comment", "")

        models.Review.objects.update_or_create(
            user=request.user,
            cruise=cruise,
            defaults={"rating": rating, "comment": comment},
        )
        messages.success(request, "Review saved.")
        return redirect("cruise_detail", pk=pk)

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

class SignUpView(generic.CreateView):
    form_class = UserCreationForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("index")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response
    

@login_required
def purchase_cruise(request, pk):
    if request.method != "POST":
        return redirect("cruise_detail", pk=pk)

    cruise = get_object_or_404(models.Cruise, pk=pk)
    models.Purchase.objects.get_or_create(user=request.user, cruise=cruise)
    messages.success(request, f"Purchase registered for {cruise.name}. You can now write a review.")
    return redirect("cruise_detail", pk=pk)
