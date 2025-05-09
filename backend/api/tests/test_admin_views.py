import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.db.models import F
from api.models import (
    User, Video, CompanyProfile, ViewerProfile, WebcamRecording 
)
from django.utils import timezone
from unittest.mock import patch, MagicMock

User = get_user_model()

@pytest.fixture
def admin_user():
    """Create an admin user for testing."""    
    return User.objects.create_user(
        email='admin@example.com',
        password='testpassword',
        firebase_uid='admin_firebase_uid',
        role='admin'
    )

@pytest.fixture
def company_user():
    """Create a company user for testing."""    
    user = User.objects.create_user(
        email='company@example.com',
        password='testpassword',
        firebase_uid='company_firebase_uid',
        role='company'
    )
    CompanyProfile.objects.create(user=user, company_name='Test Company')
    return user

@pytest.fixture
def regular_user():
    """Create a regular user for testing."""    
    user = User.objects.create_user(
        email='user@example.com',
        password='testpassword',
        firebase_uid='user_firebase_uid',
        role='user'
    )
    ViewerProfile.objects.create(user=user)
    return user

@pytest.fixture
def test_video(admin_user):
    """Create a test video for testing."""    
    return Video.objects.create(
        title='Test Admin Video',
        description='Test video for admin views',
        video_url='https://example.com/admin_test_video',
        thumbnail_url='https://example.com/admin_test_thumb',
        uploader=admin_user,
        visibility='public'
    )

@pytest.fixture
def admin_client(admin_user):
    """Create an authenticated admin client."""    
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client

@pytest.fixture
def company_client(company_user):
    """Create an authenticated company client."""    
    client = APIClient()
    client.force_authenticate(user=company_user)
    return client

@pytest.fixture
def user_client(regular_user):
    """Create an authenticated regular user client."""    
    client = APIClient()
    client.force_authenticate(user=regular_user)
    return client

@pytest.mark.django_db
class TestUserSearchView:
    """Test the UserSearchView admin API."""    
    
    def test_search_user_by_email_success(self, admin_client, regular_user):
        """Test searching for a user by email successfully."""        
        url = reverse('admin-user-search')
        response = admin_client.get(url, {'email': regular_user.email})
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == regular_user.email
        assert response.data['role'] == regular_user.role
    
    def test_search_user_case_insensitive(self, admin_client, regular_user):
        """Test that user search is case insensitive."""        
        url = reverse('admin-user-search')
        response = admin_client.get(url, {'email': regular_user.email.upper()})
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == regular_user.email
    
    def test_search_user_not_found(self, admin_client):
        """Test searching for a non-existent user email."""        
        url = reverse('admin-user-search')
        response = admin_client.get(url, {'email': 'nonexistent@example.com'})
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data
    
    def test_search_user_missing_email(self, admin_client):
        """Test searching without providing an email parameter."""        
        url = reverse('admin-user-search')
        response = admin_client.get(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.data
    
    def test_search_user_unauthorized(self, user_client):
        """Test that non-admin users cannot access the endpoint."""        
        url = reverse('admin-user-search')
        response = user_client.get(url, {'email': 'test@example.com'})
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
class TestVideoManagementView:
    """Test the VideoManagementView admin API."""    
    
    def test_get_all_videos(self, admin_client, test_video):
        """Test retrieving all videos."""        
        # Create another video for testing
        Video.objects.create(
            title='Another Test Video',
            video_url='https://example.com/another_test',
            uploader=test_video.uploader
        )
        
        url = reverse('admin-videos-list')
        response = admin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
    
    def test_get_single_video(self, admin_client, test_video):
        """Test retrieving a single video by ID."""
        url = reverse('admin-video', kwargs={'video_id': test_video.id})
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == test_video.id
        assert response.data['title'] == test_video.title

    def test_get_single_video_not_found(self, admin_client):
        """Test retrieving a non-existent single video."""
        url = reverse('admin-video', kwargs={'video_id': 9999})
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_update_video(self, admin_client, test_video):
        """Test updating a video's metadata."""        
        url = reverse('admin-video', kwargs={'video_id': test_video.id})
        data = {
            'title': 'Updated Title',
            'description': 'Updated description',
            'visibility': 'private'
        }
        response = admin_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Updated Title'
        assert response.data['description'] == 'Updated description'
        assert response.data['visibility'] == 'private'
        
        # Verify database was updated
        test_video.refresh_from_db()
        assert test_video.title == 'Updated Title'
        assert test_video.visibility == 'private'
    
    def test_update_video_invalid_data(self, admin_client, test_video):
        """Test updating a video with invalid data."""        
        url = reverse('admin-video', kwargs={'video_id': test_video.id})
        data = {
            'visibility': 'invalid_visibility'
        }
        response = admin_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_delete_video(self, admin_client, test_video):
        """Test deleting a video."""        
        video_id = test_video.id
        url = reverse('admin-video', kwargs={'video_id': video_id})
        response = admin_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify video was deleted
        assert not Video.objects.filter(id=video_id).exists()
    
    def test_delete_nonexistent_video(self, admin_client):
        """Test deleting a non-existent video."""        
        url = reverse('admin-video', kwargs={'video_id': 9999})
        response = admin_client.delete(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_video_management_unauthorized(self, user_client, test_video):
        """Test that non-admin users cannot access the endpoints."""        
        url = reverse('admin-videos-list')
        response = user_client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        url = reverse('admin-video', kwargs={'video_id': test_video.id})
        response = user_client.delete(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
class TestVideoStatsView:
    """Test the VideoStatsView admin API."""    
    
    def test_get_video_stats(self, admin_client, test_video):
        """Test retrieving video statistics."""        
        # Create videos with different visibilities and categories
        Video.objects.create(
            title='Private Video',
            video_url='https://example.com/private',
            uploader=test_video.uploader,
            visibility='private',
            category='Education',
            views=50
        )
        
        Video.objects.create(
            title='Unlisted Video',
            video_url='https://example.com/unlisted',
            uploader=test_video.uploader,
            visibility='unlisted',
            category='Entertainment',
            likes=30
        )
        
        url = reverse('admin-video-stats')
        response = admin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify statistics data
        assert response.data['total_videos'] == 3
        assert response.data['visibility']['public'] == 1
        assert response.data['visibility']['private'] == 1
        assert response.data['visibility']['unlisted'] == 1
        
        # Verify categories
        categories = {cat['category']: cat['count'] for cat in response.data['categories']}
        assert 'Education' in categories
        assert 'Entertainment' in categories
        
        # Verify stats lists
        assert len(response.data['most_viewed']) == 3
        assert len(response.data['most_liked']) == 3
        assert len(response.data['recent']) == 3
    
    def test_stats_unauthorized(self, user_client):
        """Test that non-admin users cannot access the endpoint."""        
        url = reverse('admin-video-stats')
        response = user_client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
class TestPromoteToAdminView:
    """Test the PromoteToAdminView admin API."""    
    
    @patch('api.admin_views.firebase_auth.get_user')
    @patch('api.admin_views.db')
    def test_promote_user_to_admin_success(self, mock_db, mock_get_user, admin_client, regular_user):
        """Test successfully promoting a regular user to admin."""        
        # Mock Firebase auth and db
        mock_get_user.return_value = {'uid': regular_user.firebase_uid}
        
        # Create mock for Firestore document
        mock_document = MagicMock()
        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_document
        mock_db.collection.return_value = mock_collection
        
        url = reverse('admin-promote-user')
        data = {
            'user_id': regular_user.id,
            'admin_password': 'testpassword'
        }
        
        response = admin_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'user' in response.data
        assert response.data['user']['role'] == 'admin'
        assert 'Successfully promoted' in response.data['message']
        
        # Verify user was updated in the database
        regular_user.refresh_from_db()
        assert regular_user.role == 'admin'
        
        # Verify Firebase was called correctly
        mock_get_user.assert_called_once()
        mock_db.collection.assert_called_once_with('users')
        mock_collection.document.assert_called_once_with(regular_user.firebase_uid)
        mock_document.update.assert_called_once_with({'role': 'admin'})
        
        # Verify viewer profile was deleted
        assert not ViewerProfile.objects.filter(user=regular_user).exists()
    
    @patch('api.admin_views.firebase_auth.get_user')
    @patch('api.admin_views.db')
    def test_promote_company_user_to_admin(self, mock_db, mock_get_user, admin_client, company_user):
        """Test promoting a company user to admin."""        
        # Mock Firebase auth and db
        mock_get_user.return_value = {'uid': company_user.firebase_uid}
        
        # Create mock for Firestore document
        mock_document = MagicMock()
        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_document
        mock_db.collection.return_value = mock_collection
        
        url = reverse('admin-promote-user')
        data = {
            'user_id': company_user.id,
            'admin_password': 'testpassword'
        }
        
        assert CompanyProfile.objects.filter(user=company_user).exists()
        
        response = admin_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify user was updated
        company_user.refresh_from_db()
        assert company_user.role == 'admin'
        
        # Verify company profile was deleted
        assert not CompanyProfile.objects.filter(user=company_user).exists()
    
    def test_promote_missing_data(self, admin_client):
        """Test promotion API with missing data."""        
        url = reverse('admin-promote-user')
        
        # Missing password
        data1 = {'user_id': 1}
        response1 = admin_client.post(url, data1, format='json')
        assert response1.status_code == status.HTTP_400_BAD_REQUEST
        
        # Missing user_id
        data2 = {'admin_password': 'testpassword'}
        response2 = admin_client.post(url, data2, format='json')
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
    
    @patch('api.admin_views.firebase_auth.get_user')
    def test_promote_user_firebase_auth_failure(self, mock_get_user, admin_client, regular_user):
        """Test handling a Firebase authentication failure."""        
        # Mock Firebase auth to raise an exception
        mock_get_user.side_effect = Exception("Firebase auth error")
        
        url = reverse('admin-promote-user')
        data = {
            'user_id': regular_user.id,
            'admin_password': 'testpassword'
        }
        
        response = admin_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid credentials" in response.data['error']
        
        # Verify user role was not changed
        regular_user.refresh_from_db()
        assert regular_user.role == 'user'
    
    @patch('api.admin_views.firebase_auth.get_user')
    @patch('api.admin_views.db')
    def test_promote_user_firebase_db_failure(self, mock_db, mock_get_user, admin_client, regular_user):
        """Test handling a Firebase Firestore database failure during promotion."""        
        # Mock Firebase auth for the requesting admin
        mock_get_user.return_value = {'uid': admin_client.handler._force_user.firebase_uid}

        # Create mock for Firestore document that raises an exception when updated
        mock_document = MagicMock()
        mock_document.update.side_effect = Exception("Firestore error")

        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_document

        mock_db.collection.return_value = mock_collection

        url = reverse('admin-promote-user')
        data = {
            'user_id': regular_user.id,
            'admin_password': 'testpassword'
        }

        response = admin_client.post(url, data, format='json')

        # Updated to match the actual error message pattern
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "An internal error occurred while updating Firebase" in response.data['error']

        # Verify user role was rolled back in Django DB
        regular_user.refresh_from_db()
        assert regular_user.role == 'user'
    
    def test_promote_unauthorized(self, user_client, regular_user):
        """Test that non-admin users cannot access the endpoint."""        
        url = reverse('admin-promote-user')
        data = {
            'user_id': regular_user.id,
            'admin_password': 'wrongpassword'
        }
        
        response = user_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
class TestWebcamRecordingsView:
    """Test the WebcamRecordingsView admin API."""

    @pytest.fixture
    def test_webcam_recording(self, test_video, regular_user):
        """Create a test webcam recording."""
        recording = WebcamRecording.objects.create(
            video=test_video,
            recorder=regular_user,
            filename='test_recording.webm',
            recording_url='https://example.com/recordings/test_recording.webm',
            upload_status='completed'
        )
        return recording

    def test_get_webcam_recordings(self, admin_client, test_webcam_recording):
        """Test retrieving all webcam recordings as admin."""
        url = reverse('admin-webcam-recordings')
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1 # Use >= 1 in case other tests create recordings
        # Find the specific recording in the list
        found = False
        for rec_data in response.data:
            if rec_data['id'] == test_webcam_recording.id:
                assert rec_data['filename'] == 'test_recording.webm'
                assert rec_data['recording_url'] == 'https://example.com/recordings/test_recording.webm'
                assert rec_data['recorder']['email'] == test_webcam_recording.recorder.email
                assert rec_data['video']['id'] == test_webcam_recording.video.id
                found = True
                break
        assert found, "Test recording not found in the response list."


    def test_filter_by_user(self, admin_client, test_webcam_recording, admin_user):
        """Test filtering webcam recordings by user."""
        # Create another recording with a different user
        WebcamRecording.objects.create(
            video=test_webcam_recording.video,
            recorder=admin_user,
            filename='admin_recording.webm',
            recording_url='https://example.com/recordings/admin_recording.webm'
        )

        # Filter by regular user
        url = reverse('admin-webcam-recordings')
        response = admin_client.get(url, {'user_id': test_webcam_recording.recorder.id})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['filename'] == 'test_recording.webm'

        # Filter by admin user
        response = admin_client.get(url, {'user_id': admin_user.id})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['filename'] == 'admin_recording.webm'

    def test_filter_by_video(self, admin_client, test_webcam_recording, admin_user):
        """Test filtering webcam recordings by video."""
        # Create another video and recording
        new_video = Video.objects.create(
            title='Another Test Video',
            video_url='https://example.com/another_video.mp4',
            uploader=admin_user
        )

        WebcamRecording.objects.create(
            video=new_video,
            recorder=test_webcam_recording.recorder,
            filename='another_recording.webm',
            recording_url='https://example.com/recordings/another_recording.webm'
        )

        # Filter by original video
        url = reverse('admin-webcam-recordings')
        response = admin_client.get(url, {'video_id': test_webcam_recording.video.id})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['filename'] == 'test_recording.webm'

        # Filter by new video
        response = admin_client.get(url, {'video_id': new_video.id})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['filename'] == 'another_recording.webm'

    def test_filter_by_status(self, admin_client, test_webcam_recording):
        """Test filtering webcam recordings by upload status."""
        # Create another recording with different status
        WebcamRecording.objects.create(
            video=test_webcam_recording.video,
            recorder=test_webcam_recording.recorder,
            filename='pending_recording.webm',
            recording_url='https://example.com/recordings/pending_recording.webm',
            upload_status='pending'
        )

        # Filter by completed status
        url = reverse('admin-webcam-recordings')
        response = admin_client.get(url, {'status': 'completed'})

        assert response.status_code == status.HTTP_200_OK
        # Check that only completed recordings are returned
        assert len(response.data) >= 1
        assert all(rec['upload_status'] == 'completed' for rec in response.data)
        assert any(rec['filename'] == 'test_recording.webm' for rec in response.data)


        # Filter by pending status
        response = admin_client.get(url, {'status': 'pending'})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['filename'] == 'pending_recording.webm'
        assert response.data[0]['upload_status'] == 'pending'

    def test_unauthorized_access(self, user_client, test_webcam_recording):
        """Test that non-admin users cannot access the endpoint."""
        url = reverse('admin-webcam-recordings')
        response = user_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN