from django.test import TestCase, override_settings
from django.urls import reverse


class CronSweepTests(TestCase):
    url = reverse("cron_sweep")

    @override_settings(CRON_SECRET="")
    def test_disabled_without_secret(self):
        self.assertEqual(self.client.get(self.url).status_code, 503)

    @override_settings(CRON_SECRET="s3cret")
    def test_rejects_missing_or_wrong_token(self):
        self.assertEqual(self.client.get(self.url).status_code, 401)
        self.assertEqual(self.client.get(self.url, HTTP_AUTHORIZATION="Bearer nope").status_code, 401)

    @override_settings(CRON_SECRET="s3cret")
    def test_runs_sweep_with_valid_token(self):
        response = self.client.get(self.url, HTTP_AUTHORIZATION="Bearer s3cret")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reminders_sent"], 0)


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "bucket_name": "retro-media",
                "endpoint_url": "https://br-x.storage.example.neon.tech",
                "custom_domain": "br-x.storage.example.neon.tech/retro-media",
                "querystring_auth": False,
                "access_key": "k",
                "secret_key": "s",
            },
        },
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class MediaStorageTests(TestCase):
    def test_cover_urls_point_at_public_bucket(self):
        from django.core.files.storage import storages

        url = storages["default"].url("covers/dune.jpg")
        self.assertEqual(url, "https://br-x.storage.example.neon.tech/retro-media/covers/dune.jpg")
