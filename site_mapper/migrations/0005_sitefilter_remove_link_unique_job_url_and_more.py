# Generated by Django 5.0.4 on 2025-05-03 00:36

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('site_mapper', '0004_consolidated_link_structure'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteFilter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['url'],
            },
        ),
        migrations.RemoveConstraint(
            model_name='link',
            name='unique_job_url',
        ),
        migrations.RemoveIndex(
            model_name='link',
            name='site_mapper_job_depth_idx',
        ),
        migrations.RemoveIndex(
            model_name='link',
            name='site_mapper_job_proc_idx',
        ),
        migrations.RemoveIndex(
            model_name='link',
            name='site_mapper_startin_idx',
        ),
        migrations.RemoveField(
            model_name='link',
            name='parent_id',
        ),
        migrations.AddField(
            model_name='link',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='site_mapper.link'),
        ),
        migrations.AlterField(
            model_name='link',
            name='depth',
            field=models.IntegerField(default=0, help_text='Click depth level from starting URL'),
        ),
        migrations.AlterField(
            model_name='link',
            name='file_path',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AlterField(
            model_name='link',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='link',
            name='job',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='links', to='site_mapper.sitemapjob'),
        ),
        migrations.AlterField(
            model_name='link',
            name='starting_url',
            field=models.URLField(blank=True, help_text='The root URL this link belongs to', max_length=500, null=True),
        ),
        migrations.AlterField(
            model_name='link',
            name='type',
            field=models.CharField(choices=[('page', 'Web Page'), ('pdf', 'PDF Document'), ('docx', 'Word Document'), ('xlsx', 'Excel Document'), ('other', 'Other'), ('broken', 'Broken Link')], default='page', max_length=10),
        ),
        migrations.AlterField(
            model_name='link',
            name='url',
            field=models.URLField(max_length=500),
        ),
        migrations.AlterField(
            model_name='sitemapjob',
            name='current_depth',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='sitemapjob',
            name='max_depth',
            field=models.IntegerField(default=3),
        ),
        migrations.AlterField(
            model_name='sitemapjob',
            name='start_urls',
            field=models.TextField(),
        ),
    ]
