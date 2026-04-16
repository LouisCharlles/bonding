from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Profile, ProfileVerificationAttempt
from ..serializers import ProfileVerificationAttemptSerializer, VerificationSelfieSerializer
from ..services.external_integrations import IntegrationError
from ..services.verification import compare_profile_selfie


class ProfileVerificationAttemptView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        attempts = request.user.profile.verification_attempts.all()
        return Response(ProfileVerificationAttemptSerializer(attempts, many=True, context={"request": request}).data)

    def post(self, request):
        profile = request.user.profile
        serializer = VerificationSelfieSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attempt = ProfileVerificationAttempt.objects.create(profile=profile)
        serializer.save(attempt=attempt)

        try:
            result = compare_profile_selfie(profile, attempt.selfie)
        except IntegrationError as error:
            attempt.status = ProfileVerificationAttempt.STATUS_REVIEW
            attempt.rejection_reason = str(error)
            attempt.save(update_fields=["status", "rejection_reason", "updated_at"])
            profile.verification_status = Profile.VERIFICATION_PENDING
            profile.save(update_fields=["verification_status", "updated_at"])
            return Response(ProfileVerificationAttemptSerializer(attempt, context={"request": request}).data, status=status.HTTP_202_ACCEPTED)

        attempt.status = (
            ProfileVerificationAttempt.STATUS_APPROVED
            if result.approved
            else ProfileVerificationAttempt.STATUS_REJECTED
        )
        attempt.score = result.score
        attempt.rejection_reason = result.rejection_reason
        attempt.provider_payload = result.provider_payload
        attempt.save(update_fields=["status", "score", "rejection_reason", "provider_payload", "updated_at"])

        attempt.selfie.brightness_score = result.brightness_score
        attempt.selfie.face_detected = result.face_detected
        attempt.selfie.accessories_detected = result.accessories_detected
        attempt.selfie.save(update_fields=["brightness_score", "face_detected", "accessories_detected"])

        if result.approved:
            profile.is_verified = True
            profile.verification_status = Profile.VERIFICATION_APPROVED
            profile.save(update_fields=["is_verified", "verification_status", "updated_at"])
            response_status = status.HTTP_201_CREATED
        else:
            profile.is_verified = False
            profile.verification_status = Profile.VERIFICATION_REJECTED
            profile.save(update_fields=["is_verified", "verification_status", "updated_at"])
            response_status = status.HTTP_200_OK

        return Response(ProfileVerificationAttemptSerializer(attempt, context={"request": request}).data, status=response_status)
