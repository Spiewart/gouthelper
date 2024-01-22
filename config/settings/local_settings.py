# http://ses4j.github.io/2019/05/31/django-maintaining-database-per-branch-git-hook/


def get_additional_local_settings(BRANCH, DATABASES, **kwargs):
    if not BRANCH:
        BRANCH = "development"
    db_name = f"mydbname_{BRANCH}"

    for k, obj in DATABASES.items():
        obj["NAME"] = db_name

    return {
        "DATABASES": DATABASES,
    }


# BRANCH will be updated by post-checkout git hook.
BRANCH = "main"
