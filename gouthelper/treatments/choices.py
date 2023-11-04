from decimal import Decimal

from django.db.models import Choices, IntegerChoices, TextChoices
from django.utils.translation import gettext_lazy as _


class DrugClasses(TextChoices):
    ULT = "ULT", _("Urate-lowering therapy")
    STEROID = "STEROID", _("Systemic steroid")
    ANTIINFLAMMATORY = "ANTIINFLAMMATORY", _("Anti-inflammatory")
    NSAID = "NSAID", _("Nonsteroidal anti-inflammatory drug")


class NsaidChoices(TextChoices):
    CELECOXIB = "CELECOXIB", "Celecoxib"
    DICLOFENAC = "DICLOFENAC", "Diclofenac"
    IBUPROFEN = "IBUPROFEN", "Ibuprofen"
    INDOMETHACIN = "INDOMETHACIN", "Indomethacin"
    MELOXICAM = "MELOXICAM", "Meloxicam"
    NAPROXEN = "NAPROXEN", "Naproxen"


class SteroidChoices(TextChoices):
    METHYLPREDNISOLONE = "METHYLPREDNISOLONE", "Methylprednisolone"
    PREDNISONE = "PREDNISONE", "Prednisone"


class FlarePpxChoices(TextChoices):
    CELECOXIB = "CELECOXIB", "Celecoxib"
    COLCHICINE = "COLCHICINE", "Colchicine"
    DICLOFENAC = "DICLOFENAC", "Diclofenac"
    IBUPROFEN = "IBUPROFEN", "Ibuprofen"
    INDOMETHACIN = "INDOMETHACIN", "Indomethacin"
    METHYLPREDNISOLONE = "METHYLPREDNISOLONE", "Methylprednisolone"
    MELOXICAM = "MELOXICAM", "Meloxicam"
    NAPROXEN = "NAPROXEN", "Naproxen"
    PREDNISONE = "PREDNISONE", "Prednisone"


class Freqs(TextChoices):
    BID = "BID", "Twice daily"
    BIW = "BIW", "Twice weekly"
    ONCE = "ONCE", "Once"
    QDAY = "QDAY", "Daily"
    QID = "QID", "Four times daily"
    QOTHERDAY = "QOTHERDAY", "Every other day"
    QWEEK = "QWEEK", "Weekly"
    TID = "TID", "Three times daily"
    TIW = "TIW", "Three times weekly"


class Treatments(TextChoices):
    ALLOPURINOL = "ALLOPURINOL", "Allopurinol"
    CELECOXIB = "CELECOXIB", "Celecoxib"
    COLCHICINE = "COLCHICINE", "Colchicine"
    DICLOFENAC = "DICLOFENAC", "Diclofenac"
    FEBUXOSTAT = "FEBUXOSTAT", "Febuxostat"
    IBUPROFEN = "IBUPROFEN", "Ibuprofen"
    INDOMETHACIN = "INDOMETHACIN", "Indomethacin"
    MELOXICAM = "MELOXICAM", "Meloxicam"
    METHYLPREDNISOLONE = "METHYLPREDNISOLONE", "Methylprednisolone"
    NAPROXEN = "NAPROXEN", "Naproxen"
    PREDNISONE = "PREDNISONE", "Prednisone"
    PROBENECID = "PROBENECID", "Probenecid"


class UltChoices(TextChoices):
    ALLOPURINOL = "ALLOPURINOL", "Allopurinol"
    FEBUXOSTAT = "FEBUXOSTAT", "Febuxostat"
    PROBENECID = "PROBENECID", "Probenecid"


class TrtTypes(IntegerChoices):
    ULT = 0, _("Urate-lowering therapy")
    FLARE = 1, _("Flare")
    PPX = 2, _("Prophylaxis")


class AllopurinolDoses(Decimal, Choices):
    FIFTY = Decimal("50"), _("50 mg")
    ONE = Decimal("100"), _("100 mg")
    ONEFIFTY = Decimal("150"), _("150 mg")
    TWO = Decimal("200"), _("200 mg")
    TWOFIFTY = Decimal("250"), _("250 mg")
    THREE = Decimal("300"), _("300 mg")
    THREEFIFTY = Decimal("350"), _("350 mg")
    FOUR = Decimal("400"), _("400 mg")
    FOURFIFTY = Decimal("450"), _("450 mg")
    FIVE = Decimal("500"), _("500 mg")
    FIVEFIFTY = Decimal("550"), _("550 mg")
    SIX = Decimal("600"), _("600 mg")
    SIXFIFTY = Decimal("650"), _("650 mg")
    SEVEN = Decimal("700"), _("700 mg")
    SEVENFIFTY = Decimal("750"), _("750 mg")
    EIGHT = Decimal("800"), _("800 mg")


class ColchicineDoses(Decimal, Choices):
    POINTTHREE = Decimal("0.3"), _("0.3 mg")
    POINTSIX = Decimal("0.6"), _("0.6 mg")
    ONEPOINTTWO = Decimal("1.2"), _("1.2 mg")


class FebuxostatDoses(Decimal, Choices):
    TWENTY = Decimal(20), _("20 mg")
    FORTY = Decimal(40), _("40 mg")
    SIXTY = Decimal(60), _("60 mg")
    EIGHTY = Decimal(80), _("80 mg")
    ONE = Decimal(100), _("100 mg")
    ONETWENTY = Decimal(120), _("120 mg")


class PrednisoneDoses(Decimal, Choices):
    TWOPOINTFIVE = Decimal("2.5"), _("2.5 mg")
    FIVE = Decimal(5), _("5 mg")
    TEN = Decimal(10), _("10 mg")
    FIFTEEN = Decimal(15), _("15 mg")
    TWENTY = Decimal(20), _("20 mg")
    THIRTY = Decimal(30), _("30 mg")
    FORTY = Decimal(40), _("40 mg")
    SIXTY = Decimal(60), _("60 mg")
    EIGHTY = Decimal(80), _("80 mg")


class ProbenecidDoses(Decimal, Choices):
    TWOFIFTY = Decimal(250), _("250 mg")
    FIVE = Decimal(500), _("500 mg")
    SEVENFIFTY = Decimal(750), _("750 mg")
    THOUSAND = Decimal(1000), _("1000 mg")


class DiclofenacDoses(Decimal, Choices):
    TWENTYFIVE = Decimal(25), _("25 mg")
    FIFTY = Decimal(50), _("50 mg")
    SEVENTYFIVE = Decimal(75), _("75 mg")
    ONE = Decimal(100), _("100 mg")
    ONEFIFTY = Decimal(150), _("150 mg")


class IbuprofenDoses(Decimal, Choices):
    TWO = Decimal(200), _("200 mg")
    FOUR = Decimal(400), _("400 mg")
    SIX = Decimal(600), _("600 mg")
    EIGHT = Decimal(800), _("800 mg")


class IndomethacinDoses(Decimal, Choices):
    TWENTYFIVE = Decimal(25), _("25 mg")
    FIFTY = Decimal(50), _("50 mg")


class NaproxenDoses(Decimal, Choices):
    TWOTWENTY = Decimal(220), _("220 mg")
    TWOFIFTY = Decimal(250), _("250 mg")
    FOURFORTY = Decimal(440), _("440 mg")
    FIVE = Decimal(500), _("500 mg")


class MeloxicamDoses(Decimal, Choices):
    SEVENPOINTFIVE = Decimal("7.5"), _("7.5 mg")
    FIFTEN = Decimal("15"), _("15 mg")


class CelecoxibDoses(Decimal, Choices):
    TWO = Decimal(200), _("200 mg")
    FOUR = Decimal(400), _("400 mg")


class MethylprednisoloneDoses(Decimal, Choices):
    FOUR = Decimal(4), _("4 mg")
    EIGHT = Decimal(8), _("8 mg")
    SIXTEEN = Decimal(16), _("16 mg")
    TWENTY = Decimal(20), _("20 mg")
    TWENTYFOUR = Decimal(24), _("24 mg")
    THIRTYTWO = Decimal(32), _("32 mg")
    FORTY = Decimal(40), _("40 mg")
    EIGHTY = Decimal(80), _("80 mg")
