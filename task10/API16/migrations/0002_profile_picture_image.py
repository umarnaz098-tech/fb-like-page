from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("API16", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="profile_picture",
            field=models.ImageField(
                blank=True,
                max_length=200,
                upload_to="profile_pictures/",
            ),
        ),
    ]
