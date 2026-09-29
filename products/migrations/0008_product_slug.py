from django.db import migrations, models
from django.utils.text import slugify


def populate_product_slugs(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    database = schema_editor.connection.alias
    used_slugs = set()

    for product in Product.objects.using(database).order_by('pk').iterator():
        base_slug = slugify(product.name) or f'product-{product.pk}'
        product_slug = base_slug
        suffix = 2

        while product_slug in used_slugs:
            product_slug = f'{base_slug}-{suffix}'
            suffix += 1

        used_slugs.add(product_slug)
        Product.objects.using(database).filter(pk=product.pk).update(
            slug=product_slug
        )


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0007_category_parent'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='slug',
            field=models.SlugField(blank=True, max_length=220, null=True),
        ),
        migrations.RunPython(
            populate_product_slugs,
            migrations.RunPython.noop
        ),
        migrations.AlterField(
            model_name='product',
            name='slug',
            field=models.SlugField(blank=True, max_length=220, unique=True),
        ),
    ]