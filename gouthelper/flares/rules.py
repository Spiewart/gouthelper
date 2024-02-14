import rules

from ..rules import add_object, change_object, delete_object, view_object, view_object_list

rules.add_rule("can_add_flare", add_object)
rules.add_perm("flares.can_add_flare", add_object)
rules.add_rule("can_change_flare", change_object)
rules.add_perm("flares.can_change_flare", change_object)
rules.add_rule("can_delete_flare", delete_object)
rules.add_perm("flares.can_delete_flare", delete_object)
rules.add_rule("can_view_flare", view_object)
rules.add_perm("flares.can_view_flare", view_object)
rules.add_rule("can_view_flare_list", view_object_list)
rules.add_perm("flares.can_view_flare_list", view_object_list)
