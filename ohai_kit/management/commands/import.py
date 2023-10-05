from os.path import isfile, join
from zipfile import ZipFile
import json
from django.core.management.base import BaseCommand, CommandError
from ohai_kit.models import Project, WorkStep, StepPicture, StepAttachment, StepCheck, ProjectSet
from ohai_kit.models import JobInstance, WorkReceipt
from django.conf import settings


class Command(BaseCommand):
    args = '<backup_path>'
    help = """
    This command overrides existing project definitions etc from the
    data that the corresponding backup command generates.  CAUTION:
    this will delete all work reciepts, and is only intended for
    syncing your public instance with the cannonical internal
    instance!
    """

    def handle(self, *args, **options):
        backup_path = args[0]
        backup = ZipFile(backup_path, 'r')

        # Before deleting or overwritting anything, parse out the
        # saved project data to determine roughly if this archive
        # contains anything we're actually interested in, and record
        # image paths:
        photo_paths = []
        data = json.loads(backup.read("project_data.json"))
        assert len(data) > 0
        assert data.has_key("projects")
        assert data.has_key("groups")
        for project in data["projects"]:
            assert project.has_key("name")
            assert project.has_key("abstract")
            assert project.has_key("photo")
            assert project.has_key("steps")
            photo_paths.append(project["photo"])
            for work_step in project["steps"]:
                photo_paths.extend(photo["path"] for photo in work_step["photos"])
        # That is probably good enough.  Now, let's drop pretty much
        # the entire database!  Nothing could possibly go wrong!
        for model in [Project, WorkStep, StepPicture, StepAttachment,
                      StepCheck, JobInstance, WorkReceipt, ProjectSet]:
            self.stdout.write(
                "Dropping all tables for {0}!".format(str(model)))
            model.objects.all().delete()

        for project_index, project in enumerate(data["projects"], start=1):
            self.stdout.write(
                " - restoring project {0}...".format(project["name"]))
            project_record = Project()
            if project.has_key("slug"):
                project_record.slug = project["slug"]
            project_record.name = project["name"]
            project_record.abstract = project["abstract"]
            project_record.photo = project["photo"]
            project_record.order = project_index
            project_record.save()

            for step_index, work_step in enumerate(project["steps"], start=1):
                step_record = WorkStep()
                step_record.project = project_record
                step_record.name = work_step["name"]
                step_record.description = work_step["description"]
                step_record.sequence_number = step_index*10
                step_record.save()
                for photo_index, photo in enumerate(work_step["photos"], start=1):
                    photo_record = StepPicture()
                    photo_record.step = step_record
                    photo_record.photo = photo["path"]
                    photo_record.caption = photo["caption"]
                    photo_record.image_order = photo_index * 10
                    photo_record.save()
                if work_step.has_key("attchs"):
                    for attachment_index, att in enumerate(work_step["attchs"], start=1):
                        att_record = StepAttachment()
                        att_record.step = step_record
                        att_record.attachment = att["path"]
                        att_record.caption = att["caption"]
                        att_record.order = attachment_index
                        if att["thumb"]:
                            att_record.thumbnail = att["thumb"]
                        att_record.save()
                for check_index, check in enumerate(work_step["checks"], start=1):
                    check_record = StepCheck()
                    check_record.step = step_record
                    check_record.message = check
                    check_record.check_order = check_index * 10
                    check_record.save()
        for group_index, group in enumerate(data["groups"], start=1):
            group_record = ProjectSet()
            if group.has_key("slug"):
                group_record.slug = group["slug"]
            group_record.name = group["name"]
            group_record.abstract = group["abstract"]
            group_record.photo = group["photo"]
            group_record.order = group_index
            group_record.legacy = bool(group["legacy"])
            group_record.private = bool(group["private"])
            if group.has_key("index_mode"):
                group_record.index_mode = bool(group["index_mode"])
            group_record.save()

            for slug in group["projects"]:
                try:
                    project = Project.objects.get(slug=slug)
                except:
                    self.stdout.write(" ! could not find project for given slug: {0}".format(slug))
                    continue
                group_record.projects.add(project)
            group_record.save()

        # All done!
        self.stdout.write("Done!")
