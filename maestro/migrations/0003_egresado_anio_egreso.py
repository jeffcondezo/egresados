from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('maestro', '0002_alter_egresado_options_egresado_anio_ingreso_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='egresado',
            name='anio_egreso',
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                verbose_name='Año de egreso',
            ),
        ),
    ]
