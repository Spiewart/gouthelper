import rules

from ..rules import add_object, change_object, view_object

rules.add_rule("can_add_goalurate", add_object)
rules.add_perm("goalurates.can_add_goalurate", add_object)
rules.add_rule("can_change_goalurate", change_object)
rules.add_perm("goalurates.can_change_goalurate", change_object)
rules.add_rule("can_view_goalurate", view_object)
rules.add_perm("goalurates.can_view_goalurate", view_object)
