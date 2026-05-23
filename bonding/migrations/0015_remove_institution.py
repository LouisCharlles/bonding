from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("bonding", "0014_alter_message_provider_payload_and_more"),
    ]

    operations = [
        migrations.DeleteModel(
            name="InstitutionDomain",
        ),
        migrations.DeleteModel(
            name="Institution",
        ),
    ]
