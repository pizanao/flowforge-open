from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("flowforge", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="WorkflowTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=150)),
                ("description", models.TextField(blank=True, default="")),
                ("category", models.CharField(blank=True, default="", max_length=50)),
                ("tags", models.JSONField(blank=True, default=list)),
                ("nodes_data", models.JSONField(default=list, help_text="Lista de nós: [{_ref, node_type, label, config, position_x, position_y}]")),
                ("edges_data", models.JSONField(default=list, help_text="Lista de edges: [{source_ref, target_ref, source_handle, label}]")),
            ],
            options={
                "ordering": ["name"],
            },
        ),
    ]
