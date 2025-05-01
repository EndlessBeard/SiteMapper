from django.db import migrations, models
import django.db.models.deletion
import uuid as uuid_lib

class Migration(migrations.Migration):
    dependencies = [
        ('site_mapper', '0003_link_job'),
    ]

    operations = [
        # First, remove the old Link model entirely
        migrations.DeleteModel(
            name='Link',
        ),
        
        # Then create a new Link model with the desired structure
        migrations.CreateModel(
            name='Link',
            fields=[
                ('id', models.UUIDField(default=uuid_lib.uuid4, primary_key=True, editable=False)),
                ('url', models.URLField(max_length=2048)),
                ('type', models.CharField(choices=[('page', 'Web Page'), ('pdf', 'PDF Document'), ('docx', 'Word Document'), ('xlsx', 'Excel Document')], default='page', max_length=10)),
                ('parent_id', models.UUIDField(blank=True, null=True)),
                ('starting_url', models.URLField(blank=True, max_length=2048, null=True)),
                ('depth', models.IntegerField(default=0)),
                ('link_text', models.TextField(blank=True, null=True)),
                ('processed', models.BooleanField(default=False)),
                ('file_path', models.CharField(blank=True, max_length=512, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='links', to='site_mapper.sitemapjob')),
            ],
            options={
                'indexes': [
                    models.Index(fields=['job', 'depth'], name='site_mapper_job_depth_idx'),
                    models.Index(fields=['job', 'processed'], name='site_mapper_job_proc_idx'),
                    models.Index(fields=['starting_url'], name='site_mapper_startin_idx'),
                ],
                'constraints': [
                    models.UniqueConstraint(fields=('job', 'url'), name='unique_job_url'),
                ],
            },
        ),
    ]