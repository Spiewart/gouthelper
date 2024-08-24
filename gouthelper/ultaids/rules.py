import rules

from ..rules import add_object, change_object, view_object

rules.add_rule("can_add_ultaid", add_object)
rules.add_perm("ultaids.can_add_ultaid", add_object)
rules.add_rule("can_change_ultaid", change_object)
rules.add_perm("ultaids.can_change_ultaid", change_object)
rules.add_rule("can_view_ultaid", view_object)
rules.add_perm("ultaids.can_view_ultaid", view_object)
