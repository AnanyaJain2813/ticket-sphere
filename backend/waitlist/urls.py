from django.urls import path
from waitlist.views import CancelWaitlistView, JoinWaitlistView, UserWaitlistView

urlpatterns = [
    path('waitlist/', UserWaitlistView.as_view(), name='waitlist-list'),
    path('waitlist/join/', JoinWaitlistView.as_view(), name='waitlist-join'),
    path('waitlist/<uuid:entry_id>/cancel/', CancelWaitlistView.as_view(), name='waitlist-cancel'),
]
