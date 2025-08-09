from django.core.management.base import BaseCommand
from autoreply.services.gmail import stop_gmail_watch


class Command(BaseCommand):
    help = "Stops the Gmail push notification watch for the delegated service account."

    def handle(self, *args, **kwargs):
        self.stdout.write("Attempting to stop the Gmail watch...")
        try:
            stop_gmail_watch()
            self.stdout.write(
                self.style.SUCCESS("Successfully stopped the Gmail watch subscription.")
            )
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"An error occurred while trying to stop the watch: {e}")
            )
