import rules

from ..rules import add_object, change_object, view_object

rules.add_rule("can_add_ppxaid", add_object)
rules.add_perm("ppxaids.can_add_ppxaid", add_object)
rules.add_rule("can_change_ppxaid", change_object)
rules.add_perm("ppxaids.can_change_ppxaid", change_object)
rules.add_rule("can_view_ppxaid", view_object)
rules.add_perm("ppxaids.can_view_ppxaid", view_object)
