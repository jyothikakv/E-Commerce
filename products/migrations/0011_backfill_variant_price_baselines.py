from django.db import migrations
from django.utils import timezone


def backfill_variant_price_baselines(apps, schema_editor):
    ProductVariant = apps.get_model('products', 'ProductVariant')
    PriceHistory = apps.get_model('products', 'PriceHistory')
    database = schema_editor.connection.alias
    history = PriceHistory.objects.using(database)
    baseline_time = timezone.now()

    for variant in ProductVariant.objects.using(database).iterator():
        has_base_price = history.filter(
            variant_id=variant.pk,
            price_type__in=['original', 'updated']
        ).exists()
        if not has_base_price:
            history.create(
                variant_id=variant.pk,
                price=variant.price,
                price_type='original',
                start_date=baseline_time
            )


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0010_alter_pricehistory_price_type'),
    ]

    operations = [
        migrations.RunPython(
            backfill_variant_price_baselines,
            migrations.RunPython.noop
        ),
    ]
