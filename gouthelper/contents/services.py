from pathlib import Path

from .choices import Contexts


class CreateOrUpdateContents:
    def __init__(self, apps, path):
        self.apps = apps
        self.path = path

    Contexts = Contexts

    def get_context(self, markdown_file):
        # Check if the file is in a subdirectory
        if markdown_file.parent != Path(self.path):
            # Assign the subdirectory name to the context attr
            context = self.Contexts(markdown_file.parent.with_suffix("").name[:-1].upper())
        # Otherwise assign context to None
        else:
            context = None
        return context

    def get_slug_and_tag(self, markdown_file):
        # Get the markdown file's name without the file type and set it as a slug
        slug_tag = markdown_file.with_suffix("").name.rsplit("_", 1)
        slug = slug_tag[0]
        # Check if the file has a tag
        if len(slug_tag) > 1:
            # Assign the tag to the tag attr
            tag = slug_tag[1]
        # Otherwise assign tag to None
        else:
            tag = None
        return slug, tag

    def update_or_create(self):
        Content = self.apps.get_model("contents", "Content")
        for markdown_file in Path(self.path).glob("**/*.md"):
            context = self.get_context(markdown_file)
            slug, tag = self.get_slug_and_tag(markdown_file)
            # Get the markdown file's contents
            with open(markdown_file) as f:
                text = f.read()
            # Get the Content object, or create it if it doesn't exist
            Content.objects.update_or_create(slug=slug, context=context, tag=tag, defaults={"text": text})


def create_or_update_contents(apps, schema_editor):
    """Method that iterates over the gouthelper/markdown directory
    and creates or updates Content objects for each markdown file.
    Sets Content slug field according to the subdirectory name."""
    CreateOrUpdateContents(apps, "gouthelper/markdown").update_or_create()
