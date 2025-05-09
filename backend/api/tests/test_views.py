import pytest
import uuid
from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import F

from api.models import (
    User, Video, ViewerProfile, VideoLike, VideoShare, VideoView, WebcamRecording
)

@pytest.fixture
def api_client():
    """Fixture to provide an API client instance."""
    return APIClient()

@pytest.fixture
def test_user(db):
    """Fixture to create a regular user."""
    user = User.objects.create_user(
        email="test@example.com",
        firebase_uid="testuid123",
        password="testpassword",
        role="user"
    )
    return user

@pytest.fixture
def authenticated_client(api_client, test_user):
    """Fixture to provide an authenticated API client."""
    api_client.force_authenticate(user=test_user)
    return api_client

@pytest.fixture
def test_video(db, test_user):
    """Fixture to create a test video."""
    video = Video.objects.create(
        title="Test Video Feed",
        description="A video for testing the feed.",
        category="Testing",
        visibility="public",
        video_url="https://example.com/feed_video",
        thumbnail_url="https://example.com/feed_thumb",
        uploader=test_user,
        duration="05:00"
    )
    return video

@pytest.fixture
def test_video_private(db, test_user):
    """Fixture to create a private test video."""
    video = Video.objects.create(
        title="Private Test Video",
        description="A private video for testing.",
        category="Testing",
        visibility="private",
        video_url="https://example.com/private_video",
        thumbnail_url="https://example.com/private_thumb",
        uploader=test_user,
        duration="03:00"
    )
    return video

@pytest.fixture
def test_video_view(db, test_user, test_video):
    """Fixture to create a video view record."""
    view = VideoView.objects.create(
        video=test_video,
        viewer=test_user,
        viewed_at=timezone.now()
    )
    return view

@pytest.fixture
def test_video_like(db, test_user, test_video):
    """Fixture to create a video like record."""
    # First increment the video's likes counter
    test_video.likes = 1
    test_video.save()
    
    # Then create the like record
    like = VideoLike.objects.create(
        video=test_video,
        user=test_user,
        liked_at=timezone.now()
    )
    return like

@pytest.fixture
def test_video_share(db, test_user, test_video):
    """Fixture to create a video share record."""
    share_token = str(uuid.uuid4())
    share = VideoShare.objects.create(
        video=test_video,
        created_by=test_user,
        share_token=share_token,
        active=True
    )
    return share

@pytest.fixture
def company_user(db):
    """Fixture to create a company user."""
    user = User.objects.create_user(
        email="company@example.com",
        firebase_uid="companyuid123",
        password="companypassword",
        role="company"
    )
    return user

@pytest.fixture
def admin_user(db):
    """Fixture to create an admin user."""
    user = User.objects.create_user(
        email="admin@example.com",
        firebase_uid="adminuid123",
        password="adminpassword",
        role="admin"
    )
    return user

@pytest.fixture
def company_authenticated_client(api_client, company_user):
    """Fixture to provide an authenticated API client for company user."""
    api_client.force_authenticate(user=company_user)
    return api_client

@pytest.fixture
def admin_authenticated_client(api_client, admin_user):
    """Fixture to provide an authenticated API client for admin user."""
    api_client.force_authenticate(user=admin_user)
    return api_client

@pytest.fixture
def company_video(db, company_user):
    """Fixture to create a test video owned by a company user."""
    video = Video.objects.create(
        title="Company Video",
        description="A video for testing",
        category="Testing",
        visibility="public",
        video_url="https://example.com/company_video",
        thumbnail_url="https://example.com/company_thumb",
        uploader=company_user,
        duration="04:30"
    )
    return video

@pytest.fixture
def viewer_profile(db, test_user):
    """Fixture to create a viewer profile."""
    profile, _ = ViewerProfile.objects.get_or_create(
        user=test_user,
        defaults={
            'points': 0,
            'points_earned': 0,
            'points_redeemed': 0,
            'onboarding_completed': True
        }
    )
    return profile

@pytest.mark.django_db
class TestOnboardingAPIView:
    def test_onboarding_update_success(self, authenticated_client, test_user):
        """Test successfully updating the viewer profile via onboarding."""
        url = reverse('onboarding')
        data = {
            "birthday": "1995-05-15",
            "gender": "Female",
            "country": "Canada",
            "city": "Toronto",
            "education_level": "Master's",
            "occupation": "Developer",
            "content_preferences": ["Tech", "Gaming"]
        }
        response = authenticated_client.put(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        viewer_profile = ViewerProfile.objects.get(user=test_user)
        assert viewer_profile.birthday.strftime('%Y-%m-%d') == "1995-05-15"
        assert viewer_profile.gender == "Female"
        assert viewer_profile.country == "Canada"
        assert viewer_profile.city == "Toronto"
        assert viewer_profile.education_level == "Master's"
        assert viewer_profile.occupation == "Developer"
        assert viewer_profile.content_preferences == ["Tech", "Gaming"]
        assert viewer_profile.onboarding_completed is True

    def test_onboarding_update_partial_success(self, authenticated_client, test_user):
        """Test partially updating the viewer profile."""
        ViewerProfile.objects.get_or_create(user=test_user, defaults={'country': 'Initial Country'})
        url = reverse('onboarding')
        data = {
            "city": "Vancouver",
            "occupation": "Designer"
        }
        response = authenticated_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        viewer_profile = ViewerProfile.objects.get(user=test_user)
        assert viewer_profile.city == "Vancouver"
        assert viewer_profile.occupation == "Designer"
        assert viewer_profile.onboarding_completed is True

    def test_onboarding_update_invalid_data(self, authenticated_client):
        """Test updating with invalid data (e.g., invalid date format)."""
        url = reverse('onboarding')
        data = {"birthday": "invalid-date-format"}
        response = authenticated_client.put(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'birthday' in response.data

    def test_onboarding_unauthenticated(self, api_client):
        """Test accessing onboarding endpoint without authentication."""
        url = reverse('onboarding')
        data = {"country": "USA"}
        response = api_client.put(url, data, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
class TestVideoFeedView:
    def test_video_feed_list(self, api_client, test_video):
        """Test retrieving the list of videos for the feed."""
        Video.objects.create(
            title="Another Video",
            video_url="https://example.com/another_video",
            uploader=test_video.uploader,
            visibility="public"  # Set visibility to public
        )
        url = reverse('video-feed')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_video_feed_empty(self, api_client):
        """Test retrieving the feed when there are no videos."""
        url = reverse('video-feed')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0

@pytest.mark.django_db
class TestVideoDetailView:
    def test_video_detail_retrieve(self, api_client, test_video):
        """Test retrieving the details of a specific video."""
        url = reverse('video-detail', kwargs={'video_identifier': test_video.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == test_video.id
        assert response.data['title'] == test_video.title

    def test_video_detail_not_found(self, api_client):
        """Test retrieving a video that does not exist."""
        url = reverse('video-detail', kwargs={'video_identifier': 999})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_video_detail_by_share_token(self, api_client, test_video_share):
        """Test retrieving a video using a share token."""
        url = reverse('video-detail', kwargs={'video_identifier': test_video_share.share_token})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == test_video_share.video.id
        assert response.data['title'] == test_video_share.video.title

        test_video_share.refresh_from_db()
        assert test_video_share.access_count == 1

    def test_video_detail_invalid_uuid(self, api_client):
        """Test retrieving a video with an invalid UUID format."""
        url = reverse('video-detail', kwargs={'video_identifier': 'not-a-valid-uuid'})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'Resource not found' in response.data['error']

    def test_video_detail_nonexistent_share_token(self, api_client):
        """Test retrieving a video with a non-existent share token."""
        url = reverse('video-detail', kwargs={'video_identifier': str(uuid.uuid4())})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_video_detail_should_not_change_privacy(self, api_client, test_video):
        """Test that video detail view always returns video data regardless of privacy rules."""
        url = reverse('video-detail', kwargs={'video_identifier': test_video.pk})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == test_video.id

    def test_video_detail_already_private(self, api_client, test_video_private):
        """Test retrieving a video that is already private."""
        url = reverse('video-detail', kwargs={'video_identifier': test_video_private.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {"error": "This video is no longer available"}

    def test_get_video_by_id_private_as_owner(self, api_client, test_video_private, test_user):
        """Test owner access to their private video."""
        # Set the uploader to test_user to simulate ownership
        test_video_private.uploader = test_user
        test_video_private.save()
        
        api_client.force_authenticate(user=test_user)
        url = reverse('video-detail', kwargs={'video_identifier': str(test_video_private.id)})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == test_video_private.id
        assert response.data['title'] == test_video_private.title

    def test_get_video_by_id_private_as_admin(self, api_client, test_video_private, admin_user):
        """Test admin access to a private video."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('video-detail', kwargs={'video_identifier': str(test_video_private.id)})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == test_video_private.id
        assert response.data['title'] == test_video_private.title

    def test_get_video_by_inactive_share_token(self, api_client, test_video_share):
        """Test accessing a video via inactive share token."""
        # Make the share inactive
        test_video_share.active = False
        test_video_share.save()
        
        url = reverse('video-detail', kwargs={'video_identifier': str(test_video_share.share_token)})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.django_db
class TestRecordVideoViewAPI:
    @patch('api.views.VideoViewService.record_view', autospec=True)
    def test_record_view_success(self, mock_record_view, api_client, test_video):
        """Test successfully recording a video view via service."""
        mock_record_view.return_value = (test_video, 42, False)
        url = reverse('record-video-view', kwargs={'video_id': test_video.pk})
        response = api_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['views'] == 42
        assert response.data['privacy_changed'] is False
        assert mock_record_view.call_count == 1

    def test_record_view_video_not_found(self, api_client):
        """Test recording a view for a non-existent video."""
        url = reverse('record-video-view', kwargs={'video_id': 9999})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_record_view_private_video(self, api_client, test_video_private):
        """Test recording a view for a private video."""
        url = reverse('record-video-view', kwargs={'video_id': test_video_private.pk})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {"error": "Video is private"}

    @patch('api.views.VideoViewService.record_view', autospec=True)
    def test_record_view_privacy_flag(self, mock_record_view, api_client, test_video):
        """Test recording a view that indicates privacy change."""
        mock_record_view.return_value = (test_video, 100, True)
        url = reverse('record-video-view', kwargs={'video_id': test_video.pk})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['views'] == 100
        assert response.data['privacy_changed'] is True
        assert mock_record_view.call_count == 1

    def test_record_view_anonymous(self, api_client, test_video):
        """Test recording a view without authentication."""
        url = reverse('record-video-view', kwargs={'video_id': test_video.id})
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert 'views' in response.data
        
        # Verify view was recorded
        test_video.refresh_from_db()
        assert test_video.views > 0

    @patch('api.views.VideoViewService.record_view')
    def test_record_view_privacy_changed(self, mock_record_view, api_client, test_video, test_user):
        """Test recording a view that changes video privacy."""
        # Mock the service to indicate privacy change
        mock_record_view.return_value = (test_video, 5, True)
        
        api_client.force_authenticate(user=test_user)
        url = reverse('record-video-view', kwargs={'video_id': test_video.id})
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['views'] == 5
        assert response.data['privacy_changed'] is True
        
        # Verify the service was called
        mock_record_view.assert_called_once_with(test_video.id, test_user)

@pytest.mark.django_db
class TestToggleVideoLikeAPI:
    def test_toggle_like_create(self, authenticated_client, test_user, test_video):
        """Test creating a new like for a video."""
        url = reverse('toggle-video-like', kwargs={'video_id': test_video.pk})
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['liked'] is True
        assert response.data['likes'] == 1

        like_exists = VideoLike.objects.filter(video=test_video, user=test_user).exists()
        assert like_exists is True

        test_video.refresh_from_db()
        assert test_video.likes == 1

    def test_toggle_like_delete(self, authenticated_client, test_user, test_video_like):
        """Test removing an existing like from a video."""
        url = reverse('toggle-video-like', kwargs={'video_id': test_video_like.video.pk})
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['liked'] is False
        assert response.data['likes'] == 0

        like_exists = VideoLike.objects.filter(video=test_video_like.video, user=test_user).exists()
        assert like_exists is False

        test_video_like.video.refresh_from_db()
        assert test_video_like.video.likes == 0

    def test_toggle_like_unauthenticated(self, api_client, test_video):
        """Test that unauthenticated users cannot like videos."""
        url = reverse('toggle-video-like', kwargs={'video_id': test_video.pk})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_toggle_like_nonexistent_video(self, authenticated_client):
        """Test liking a non-existent video."""
        url = reverse('toggle-video-like', kwargs={'video_id': 9999})
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch('api.views.VideoLikeService.toggle_like')
    def test_toggle_like_service_returns_none(self, mock_toggle_like, authenticated_client, test_video):
        """Test when the service returns None for video (e.g., authentication issue)."""
        # Mock the service to return None for video
        mock_toggle_like.return_value = (None, False, 0)
        
        url = reverse('toggle-video-like', kwargs={'video_id': test_video.id})
        response = authenticated_client.post(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'error' in response.data
        assert response.data['error'] == 'Authentication required'
        
        # Verify the service was called
        mock_toggle_like.assert_called_once_with(test_video.id, authenticated_client.handler._force_user)

@pytest.mark.django_db
class TestCreateVideoShareAPI:
    def test_create_share_success(self, authenticated_client, test_user, test_video):
        """Test successfully creating a share link for a video."""
        url = reverse('create-video-share', kwargs={'video_id': test_video.pk})
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_201_CREATED
        assert 'share_token' in response.data
        assert 'share_url' in response.data

        share = VideoShare.objects.get(share_token=response.data['share_token'])
        assert share.video == test_video
        assert share.created_by == test_user

    def test_create_share_unauthenticated(self, api_client, test_video):
        """Test that unauthenticated users cannot create share links."""
        url = reverse('create-video-share', kwargs={'video_id': test_video.pk})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_share_nonexistent_video(self, authenticated_client):
        """Test creating a share link for a non-existent video."""
        url = reverse('create-video-share', kwargs={'video_id': 9999})
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch('api.views.VideoShareService.create_share')
    def test_create_share_service_returns_none(self, mock_create_share, authenticated_client, test_video):
        """Test when the service returns None (e.g., authentication issue)."""
        # Mock the service to return None
        mock_create_share.return_value = None
        
        url = reverse('create-video-share', kwargs={'video_id': test_video.id})
        response = authenticated_client.post(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'error' in response.data
        assert response.data['error'] == 'Authentication required'
        
        # Verify the service was called
        mock_create_share.assert_called_once_with(test_video.id, authenticated_client.handler._force_user)

@pytest.mark.django_db
class TestUserHistoryAPI:
    def test_history_empty(self, authenticated_client):
        """Test retrieving user history when there are no views."""
        url = reverse('user-history')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0

    def test_history_with_views(self, authenticated_client, test_user, test_video_view):
        """Test retrieving user history when there are views."""
        another_video = Video.objects.create(
            title="Another History Video",
            video_url="https://example.com/another_history",
            uploader=test_user
        )
        VideoView.objects.create(
            video=another_video,
            viewer=test_user,
            viewed_at=timezone.now()
        )

        url = reverse('user-history')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        video_ids = [video['id'] for video in response.data]
        assert test_video_view.video.id in video_ids
        assert another_video.id in video_ids

    def test_history_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot access history."""
        url = reverse('user-history')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
class TestUserPointsView:
    def test_get_points(self, authenticated_client, viewer_profile):
        """Test retrieving the user's points."""
        viewer_profile.points = 15
        viewer_profile.points_earned = 20
        viewer_profile.points_redeemed = 5
        viewer_profile.save()
        
        url = reverse('user-points')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['points'] == 15
        assert response.data['points_earned'] == 20
        assert response.data['points_redeemed'] == 5
        assert 'points_value' in response.data
        assert 'conversion_rate' in response.data

    def test_get_points_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot access points information."""
        url = reverse('user-points')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
class TestWebcamUploadView:
    @patch('api.services.AzureStorageService.generate_sas_url', autospec=True)
    @patch('api.services.PointsService.award_points_for_webcam_upload', autospec=True)
    def test_webcam_upload_success(self, mock_award_points, mock_generate_sas, authenticated_client, test_video, test_user, viewer_profile):
        """Test successfully generating webcam upload URL and awarding points."""
        mock_generate_sas.side_effect = [
            'http://mockstorage.com/upload?sas=upload_token', # Upload URL
            'http://mockstorage.com/view?sas=view_token'      # View URL
        ]
        # Mock PointsService return value
        viewer_profile.points = 5 # Simulate points being added
        mock_award_points.return_value = (viewer_profile, 5)

        url = reverse('webcam-upload', kwargs={'video_id': test_video.id})
        data = {'filename': 'test_recording.webm'}
        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert 'upload_url' in response.data
        assert 'recording_id' in response.data
        assert 'points awarded' in response.data['message']
        assert response.data['total_points'] == 5
        assert mock_generate_sas.call_count == 2
        mock_award_points.assert_called_once_with(test_user)
        assert WebcamRecording.objects.filter(video=test_video, recorder=test_user).exists()

    def test_webcam_upload_missing_filename(self, authenticated_client, test_video):
        """Test uploading a webcam recording without providing a filename."""
        url = reverse('webcam-upload', kwargs={'video_id': test_video.id})
        data = {}
        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'filename' in response.data

    def test_webcam_upload_video_not_found(self, authenticated_client):
        """Test uploading a webcam recording for a video that does not exist."""
        url = reverse('webcam-upload', kwargs={'video_id': 9999})
        data = {'filename': 'test_recording.webm'}
        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch('api.services.AzureStorageService.generate_sas_url', autospec=True)
    def test_webcam_upload_sas_generation_fails(self, mock_generate_sas, authenticated_client, test_video):
        """Test uploading a webcam recording when SAS URL generation fails."""
        mock_generate_sas.side_effect = Exception("SAS generation error")

        url = reverse('webcam-upload', kwargs={'video_id': test_video.id})
        data = {'filename': 'test_recording.webm'}
        response = authenticated_client.post(url, data, format='json')

        # SAS generation errors are caught by service; controller still returns success
        assert response.status_code == status.HTTP_201_CREATED
        assert 'upload_url' in response.data
        assert response.data['upload_url'] is None
        assert 'recording_id' in response.data