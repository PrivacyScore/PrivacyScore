from django.core.management import BaseCommand

from privacyscore.scanner.tasks import handle_aborted_scans

class Command(BaseCommand):
    help = 'Runs periodic tasks like updating failed scans.'

    def handle(self, *args, **options):
        handle_aborted_scans()
