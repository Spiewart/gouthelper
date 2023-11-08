from pathlib import Path

from .choices import Contexts


def create_or_update_contents(apps, schema_editor):
    """Method that iterates over the gouthelper/markdown directory
    and creates or updates Content objects for each markdown file.
    Sets Content slug field according to the subdirectory name."""
    Content = apps.get_model("contents", "Content")
    # Iterate over markdown files in gouthelper/markdown
    for markdown_file in Path("gouthelper/markdown").glob("**/*.md"):
        print(markdown_file)
        # Check if the file is in a subdirectory
        if markdown_file.parent != Path("gouthelper/markdown"):
            # Assign the subdirectory name to the context attr
            context = Contexts(markdown_file.parent.with_suffix("").name[:-1].upper())
            print(f"context = {context}")
        # Otherwise assign context to None
        else:
            context = None
            print(f"context = {context}")
        # Get the markdown file's name without the file type and set it as a slug
        slug_tag = markdown_file.with_suffix("").name.rsplit("_", 1)
        print(f"slug_tag = {slug_tag}")
        slug = slug_tag[0]
        print(f"slug = {slug}")
        # Check if the file has a tag
        if len(slug_tag) > 1:
            # Assign the tag to the tag attr
            tag = slug_tag[1]
            print(f"tag = {tag}")
        # Otherwise assign tag to None
        else:
            tag = None
            print(f"tag = {tag}")
        # Get the markdown file's contents
        with open(markdown_file) as f:
            text = f.read()
        # Get the Content object, or create it if it doesn't exist
        Content.objects.update_or_create(slug=slug, context=context, tag=tag, defaults={"text": text})
