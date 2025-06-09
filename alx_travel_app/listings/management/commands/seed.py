from django.core.management.base import BaseCommand
from listings.models import Listing
from django.contrib.auth import get_user_model
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed the database with sample listings'

    def handle(self, *args, **kwargs):
        if not User.objects.exists():
            self.stdout.write(self.style.ERROR("Please create a user first."))
            return

        host = User.objects.first()
        titles = ['Modern Apartment', 'Cozy Cabin', 'Luxury Villa', 'Beach House']
        locations = ['New York', 'California', 'Paris', 'Tokyo']

        for i in range(10):
            Listing.objects.create(
                title=random.choice(titles),
                description='A wonderful place to stay.',
                location=random.choice(locations),
                price_per_night=random.randint(50, 500),
                host=host
            )

        self.stdout.write(self.style.SUCCESS('Successfully seeded listings.'))
