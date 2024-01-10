import rules

from ..rules import add_object, change_object, view_object

rules.add_rule("can_add_patient_flareaid", add_object)
rules.add_perm("flareaids.can_add_patient_flareaid", add_object)
rules.add_rule("can_change_patient_flareaid", change_object)
rules.add_perm("flareaids.can_change_patient_flareaid", change_object)
rules.add_rule("can_view_patient_flareaid", view_object)
rules.add_perm("flareaids.can_view_patient_flareaid", view_object)
