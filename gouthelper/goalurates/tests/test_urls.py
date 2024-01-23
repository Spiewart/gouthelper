from django.test import TestCase
from django.urls import resolve, reverse

from .factories import GoalUrateFactory, GoalUrateUserFactory


class TestGoalUrateUrls(TestCase):
    def setUp(self):
        self.goalurate = GoalUrateFactory()
        self.goalurateuser = GoalUrateUserFactory()

    def test_goalurate_about_url(self):
        path = reverse("goalurates:about")
        assert resolve(path).view_name == "goalurates:about"

    def test_goalurate_create_url(self):
        path = reverse("goalurates:create")
        assert resolve(path).view_name == "goalurates:create"

    def test_goalurate_detail_url(self):
        path = reverse("goalurates:detail", kwargs={"pk": self.goalurate.pk})
        assert resolve(path).view_name == "goalurates:detail"

    def test_goalurate_pseudopatient_create_url(self):
        path = reverse("goalurates:pseudopatient-create", kwargs={"username": self.goalurateuser.user.username})
        assert resolve(path).view_name == "goalurates:pseudopatient-create"

    def test_goalurate_pseudopatient_detail_url(self):
        path = reverse("goalurates:pseudopatient-detail", kwargs={"username": self.goalurateuser.user.username})
        assert resolve(path).view_name == "goalurates:pseudopatient-detail"

    def test_goalurate_pseudopatient_update_url(self):
        path = reverse("goalurates:pseudopatient-update", kwargs={"username": self.goalurateuser.user.username})
        assert resolve(path).view_name == "goalurates:pseudopatient-update"
