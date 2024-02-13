import rules

from ..rules import add_object, change_object, view_object

rules.add_rule("can_add_pseudopatient_ppx", add_object)
rules.add_perm("ppxs.can_add_pseudopatient_ppx", add_object)
rules.add_rule("can_change_pseudopatient_ppx", change_object)
rules.add_perm("ppxs.can_change_pseudopatient_ppx", change_object)
rules.add_rule("can_view_pseudopatient_ppx", view_object)
rules.add_perm("ppxs.can_view_pseudopatient_ppx", view_object)
