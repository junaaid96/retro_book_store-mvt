from django.core.management.base import BaseCommand

from circulation.services import send_reminders, sweep_holds


class Command(BaseCommand):
    help = "Expire stale holds, promote waitlists and send due/overdue reminders. Run hourly via cron."

    def handle(self, *args, **options):
        sweep_holds()
        sent = send_reminders()
        self.stdout.write(self.style.SUCCESS(f"Sweep complete. {sent} reminder(s) sent."))
