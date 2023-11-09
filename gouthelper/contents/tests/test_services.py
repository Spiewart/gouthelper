import tempfile  # type: ignore
from pathlib import Path  # type: ignore

import pytest  # type: ignore
from django.apps import apps  # type: ignore
from django.test import TestCase  # type: ignore

from ..choices import Contexts, Tags
from ..models import Content
from ..services import CreateOrUpdateContents, create_or_update_contents

pytestmark = pytest.mark.django_db


class TestCreateOrUpdateContents(TestCase):
    """Tests to make sure that the create_or_update_contents service method
    works as expected, doesn't raise any IntegrityErrors due to duplicates
    in the naming structure, and creates or updates the content objects
    as expected.
    """

    def setUp(self):
        # Declare all the Markdown files
        self.markdown_files = Path("gouthelper/markdown").glob("**/*.md")
        # Make sure there aren't any Content objects created at the start
        self.assertEqual(Content.objects.count(), 0)

    def test__all_markdown_created_as_content(self):
        """Test that all the Markdown files in the gouthelper/markdown directory
        are created as Content objects with the correct slug, context, and tag."""
        # Act
        create_or_update_contents(apps, None)

        # Assert
        self.assertEqual(
            len(list(self.markdown_files)),
            Content.objects.count(),
        )

        # Check that the Content objects were created with the correct slug, context, and tag
        for markdown_file in self.markdown_files:
            # Get the context the same as in the service method
            if markdown_file.parent != Path("gouthelper/markdown"):
                context = Contexts(markdown_file.parent.with_suffix("").name[:-1].upper())
            else:
                context = None
            # Get the slug and tag the same as in the service method
            slug_tag = markdown_file.with_suffix("").name.rsplit("_", 1)
            slug = slug_tag[0]
            if len(slug_tag) > 1:
                tag = slug_tag[1]
            else:
                tag = None
            self.assertTrue(
                Content.objects.filter(slug=slug, context=context, tag=tag).exists(),
            )

    def test__markdown_updated(self):
        """Test that if a Markdown file is updated, the Content object is updated
        when create_or_update_contents is called again."""
        # Create a temporary directory to avoid creating/deleting real files
        markdown_directory = tempfile.TemporaryDirectory()
        markdown_path = Path(markdown_directory.name)
        # Create some test .md files in a temporary directory
        # Format: (filename, text)
        MD1 = ("level1md.md", "Level 1 Markdown")
        MD2 = ("level2md.md", "Level 2 PPx Markdown")
        # 3rd file has an underscore in the filename, which will translate to a tag
        # and which has to be in Tags or it will raise an error
        MD3 = (f"level2md_{Tags.EXPLANATION}.md", "Level 2 PPx Markdown Tag: 1")
        # Create a subdirectory, which will translate to a context
        # and which has to be in Contexts or it will raise an error
        e = markdown_path / f"{Contexts.PPX}s"
        e.mkdir()
        # Write the Markdown files to their appropriate paths in the temporary directory
        p = markdown_path / MD1[0]
        p.write_text(MD1[1], encoding="utf-8")
        q = e / MD2[0]
        q.write_text(MD2[1], encoding="utf-8")
        r = e / MD3[0]
        r.write_text(MD3[1], encoding="utf-8")
        # Assert that the files were written correctly
        assert p.read_text(encoding="utf-8") == MD1[1]
        assert q.read_text(encoding="utf-8") == MD2[1]
        assert r.read_text(encoding="utf-8") == MD3[1]
        # Assert that the top level temporary directory has a file and a
        # subdirectory for a total length of 2
        assert len(list(markdown_path.iterdir())) == 2
        # Call update_or_create() to create the Content objects
        CreateOrUpdateContents(apps, markdown_path).update_or_create()
        # Assert that 3 contents were created
        self.assertEqual(Content.objects.count(), 3)
        # Assert that the content objects have the correct slug, context, and tag
        self.assertTrue(
            Content.objects.filter(slug="level1md", context=None, tag=None).exists(),
        )
        self.assertTrue(
            Content.objects.filter(slug="level2md", context=Contexts.PPX, tag=None).exists(),
        )
        self.assertTrue(
            Content.objects.filter(slug="level2md", context=Contexts.PPX, tag=Tags.EXPLANATION).exists(),
        )
        # Change the second Markdown file's text
        markdown_file = markdown_path / f"{Contexts.PPX}s" / "level2md.md"
        markdown_file.write_text("New text", encoding="utf-8")
        # Call update_or_create() again
        CreateOrUpdateContents(apps, markdown_path).update_or_create()
        # Get the second Markdown file's content object
        content = Content.objects.get(slug="level2md", context=Contexts.PPX, tag=None)
        # Assert that the text is changed
        self.assertEqual(content.text, "New text")
