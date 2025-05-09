# Generated by Django 5.1.7 on 2025-04-25 06:40

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0004_video_auto_private_after_video_view_limit_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="WebcamRecording",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("filename", models.CharField(max_length=255)),
                ("recording_date", models.DateTimeField(auto_now_add=True)),
                (
                    "upload_status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("upload_completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "recording_url",
                    models.URLField(blank=True, max_length=500, null=True),
                ),
                (
                    "recorder",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "video",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="webcam_recordings",
                        to="api.video",
                    ),
                ),
            ],
            options={
                "verbose_name": "Webcam Recording",
                "verbose_name_plural": "Webcam Recordings",
                "ordering": ["-recording_date"],
            },
        ),
    ]
