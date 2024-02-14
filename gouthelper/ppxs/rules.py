import rules

from ..rules import add_object, change_object, view_object

rules.add_rule("can_add_ppx", add_object)
rules.add_perm("ppxs.can_add_ppx", add_object)
rules.add_rule("can_change_ppx", change_object)
rules.add_perm("ppxs.can_change_ppx", change_object)
rules.add_rule("can_view_ppx", view_object)
rules.add_perm("ppxs.can_view_ppx", view_object)
