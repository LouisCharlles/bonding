"""
URL configuration for setup project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.conf.urls.static import static
from django.conf import settings
from rest_framework.routers import DefaultRouter
from bonding.views import (
    BlockViewSet,
    ConnectionViewSet,
    ConversationViewSet,
    CupidoRecommendationsView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    ForgotPasswordView,
    InterestViewSet,
    SpotifyTrackSearchView,
    LocationCreateOrRetrieveView,
    UserLocationPingView,
    MatchDateSuggestionsView,
    MeView,
    MessageViewSet,
    NotificationViewSet,
    PhotoViewSet,
    PreferenceViewSet,
    PremiumPlanViewSet,
    ProfileViewSet,
    ProfileVerificationAttemptView,
    PushDeviceViewSet,
    RegisterUserView,
    ReportViewSet,
    ResetPasswordView,
    StoryViewSet,
    StripePaymentIntentView,
    StripeWebhookView,
    SubscriptionViewSet,
    VerifyEmailView,
    VideoCallSessionViewSet,
    WalletViewSet,
)

router = DefaultRouter()
router.register(r'profiles', ProfileViewSet, basename='profile')
router.register(r'photos', PhotoViewSet, basename='photo')
router.register(r'connections', ConnectionViewSet, basename='connection')
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'interests', InterestViewSet, basename='interest')
router.register(r'preferences', PreferenceViewSet, basename='preference')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'blocks', BlockViewSet, basename='block')
router.register(r'stories', StoryViewSet, basename='story')
router.register(r'premium/plans', PremiumPlanViewSet, basename='premium-plan')
router.register(r'premium/subscriptions', SubscriptionViewSet, basename='subscription')
router.register(r'wallet', WalletViewSet, basename='wallet')
router.register(r'push-devices', PushDeviceViewSet, basename='push-device')
router.register(r'video-calls', VideoCallSessionViewSet, basename='video-call')
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(router.urls)),
    path('locations/', LocationCreateOrRetrieveView.as_view(), name='location-create-retrieve'),
    path('locations/ping/', UserLocationPingView.as_view(), name='location-ping'),
    path('verify-email/<int:user_id>/<uuid:token>/', VerifyEmailView.as_view(), name='verify-email'),
    path('auth/register/', RegisterUserView.as_view(), name='register-new-user'),
    path('auth/forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('auth/reset-password/<int:user_id>/<uuid:token>/', ResetPasswordView.as_view(), name='reset-password'),
    path('auth/me/', MeView.as_view(), name='me'),
    path('verification/attempts/', ProfileVerificationAttemptView.as_view(), name='profile-verification-attempts'),
    path('integrations/spotify/search/', SpotifyTrackSearchView.as_view(), name='spotify-track-search'),
    path('payments/intents/', StripePaymentIntentView.as_view(), name='stripe-payment-intent'),
    path('payments/webhooks/stripe/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('matches/<int:match_id>/date-suggestions/', MatchDateSuggestionsView.as_view(), name='match-date-suggestions'),
    path('cupido/recommendations/', CupidoRecommendationsView.as_view(), name='cupido-recommendations'),
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
] + static(settings.MEDIA_URL,
document_root=settings.MEDIA_ROOT)
