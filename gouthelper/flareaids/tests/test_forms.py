import pytest  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore

from ...medhistorys.lists import CV_DISEASES, OTHER_NSAID_CONTRAS, MedHistoryTypes
from ...treatments.choices import FlarePpxChoices
from ..forms import FlareAidForm

pytestmark = pytest.mark.django_db


class TestFlareAidForm(TestCase):
    def setUp(self):
        self.form = FlareAidForm(medallergys=FlarePpxChoices.values)
        self.factory = RequestFactory()

    def test___init__without_medallergys_raises_KeyError(self):
        with pytest.raises(KeyError):
            FlareAidForm()

    def test___init__with_medallergys_sets_medallergys(self):
        assert self.form.medallergys == FlarePpxChoices.values

    def test__forms_for_related_models_inserted(self):
        # Test that dateofbirth, gender, cvdiseases, nsaid_contras,
        # CKD, colchicine_interaction, diabetes organ transplant,
        # and medallergys forms are inserted.
        response = self.client.get(reverse("flareaids:create"))
        self.assertIn("dateofbirth-value", response.rendered_content)
        self.assertIn("gender-value", response.rendered_content)
        self.assertIn("""<label class="form-label">Cardiovascular Diseases</label>""", response.rendered_content)
        for cvdisease in CV_DISEASES:
            self.assertIn(f"{cvdisease}-value", response.rendered_content)
        self.assertIn("nsaid_contras", response.rendered_content)
        for nsaid_contra in OTHER_NSAID_CONTRAS:
            self.assertIn(f"{nsaid_contra}-value", response.rendered_content)
        self.assertIn(f"{MedHistoryTypes.CKD}-value", response.rendered_content)
        self.assertIn(f"{MedHistoryTypes.COLCHICINEINTERACTION}-value", response.rendered_content)
        self.assertIn(f"{MedHistoryTypes.DIABETES}-value", response.rendered_content)
        self.assertIn(f"{MedHistoryTypes.ORGANTRANSPLANT}-value", response.rendered_content)
        self.assertIn("medallergys", response.rendered_content)
        for medallergy in FlarePpxChoices.values:
            self.assertIn(f"medallergy_{medallergy}", response.rendered_content)
