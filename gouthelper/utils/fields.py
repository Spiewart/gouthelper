from functools import partial
from urllib.parse import urlparse

import bleach
from bleach.linkifier import LinkifyFilter
from django.conf import settings  # type: ignore
from django.urls import Resolver404, resolve  # type: ignore
from markdown import markdown  # type: ignore
from markdownfield.models import MarkdownField  # type: ignore
from markdownfield.util import blacklist_link  # type: ignore

EXTENSIONS = getattr(settings, "MARKDOWN_EXTENSIONS", ["fenced_code"])
EXTENSION_CONFIGS = getattr(settings, "MARKDOWN_EXTENSION_CONFIGS", {})


def format_link(attrs: dict[tuple, str], new: bool = False):
    """
    This is really weird and ugly, but that's how bleach linkify filters work.
    """
    try:
        p = urlparse(attrs[(None, "href")])
    except KeyError:
        # no href, probably an anchor
        return attrs

    if not any([p.scheme, p.netloc, p.path]) and p.fragment:
        # the link isn't going anywhere, probably a fragment link
        return attrs

    if hasattr(settings, "SITE_URL"):
        c = urlparse(settings.SITE_URL)
        link_is_external = p.netloc != c.netloc
    else:
        # Assume true for safety
        link_is_external = True

    if link_is_external:
        # I have overwritten this to allow for internal links to be written into markdown
        # agnostic to my development and production environment. This is a hacky solution
        # but it works for now. Internal urls must follow the pattern app_name/url_stuff/
        # Try to resolve the link
        try:
            resolve(p.path)
        # If it fails, try adding a trailing slash
        except Resolver404:
            slash_path = p.path + "/"
            # If adding a slash resolves it as an internal link, raise a ValueError
            # to alert the user that they need to add a trailing slash to their link
            try:
                resolve(slash_path)
                raise ValueError(f"Link {p.path} is missing a trailing slash")
            # If adding a slash doesn't resolve it, it's an external link
            except Resolver404:
                pass
            # link is external - secure and mark
            attrs[(None, "target")] = "_blank"
            attrs[(None, "class")] = attrs.get((None, "class"), "") + " external"
            attrs[(None, "rel")] = "nofollow noopener noreferrer"

    return attrs


class GoutHelperMarkdownField(MarkdownField):
    def pre_save(self, model_instance, add):
        value = super().pre_save(model_instance, add)

        if not self.rendered_field:
            return value

        dirty = markdown(text=value, extensions=EXTENSIONS, extension_configs=EXTENSION_CONFIGS)

        if self.validator.sanitize:
            if self.validator.linkify:
                cleaner = bleach.Cleaner(
                    tags=self.validator.allowed_tags,
                    attributes=self.validator.allowed_attrs,
                    css_sanitizer=self.validator.css_sanitizer,
                    filters=[partial(LinkifyFilter, callbacks=[format_link, blacklist_link])],
                )
            else:
                cleaner = bleach.Cleaner(
                    tags=self.validator.allowed_tags,
                    attributes=self.validator.allowed_attrs,
                    css_sanitizer=self.validator.css_sanitizer,
                )

            clean = cleaner.clean(dirty)
            setattr(model_instance, self.rendered_field, clean)
        else:
            # danger!
            setattr(model_instance, self.rendered_field, dirty)

        return value
