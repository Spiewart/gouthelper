from django.db.models import TextChoices  # type: ignore


# User types for different roles
class Roles(TextChoices):
    PATIENT = "PATIENT", "Patient"
    PROVIDER = "PROVIDER", "Provider"
    PSEUDOPATIENT = "PSEUDOPATIENT", "Pseudopatient"
    ADMIN = "ADMIN", "Admin"
