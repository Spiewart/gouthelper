import rules

from ..rules import add_object, change_object, view_object

rules.add_rule("can_add_pseudopatient_ppxaid", add_object)
rules.add_perm("ppxaids.can_add_pseudopatient_ppxaid", add_object)
rules.add_rule("can_change_pseudopatient_ppxaid", change_object)
rules.add_perm("ppxaids.can_change_pseudopatient_ppxaid", change_object)
rules.add_rule("can_view_pseudopatient_ppxaid", view_object)
rules.add_perm("ppxaids.can_view_pseudopatient_ppxaid", view_object)
