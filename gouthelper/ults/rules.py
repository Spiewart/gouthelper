import rules

from ..rules import add_object, change_object, view_object

rules.add_rule("can_add_ult", add_object)
rules.add_perm("ults.can_add_ult", add_object)
rules.add_rule("can_change_ult", change_object)
rules.add_perm("ults.can_change_ult", change_object)
rules.add_rule("can_view_ult", view_object)
rules.add_perm("ults.can_view_ult", view_object)
