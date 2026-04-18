from smartjobs.sql_guard import build_safe_sql, validate_sql_plan


def test_build_safe_sql_count_query():
    plan = validate_sql_plan(build_safe_sql('berapa jumlah lowongan data analyst di jakarta', limit=5))
    assert plan.sql.lower().startswith('select count(*)')
    assert '%data analyst%' in plan.parameter
    assert '%jakarta%' in plan.parameter


def test_build_safe_sql_listing_query():
    plan = validate_sql_plan(build_safe_sql('tampilkan data lowongan data analyst di jakarta', limit=5))
    assert 'from jobs' in plan.sql.lower()
    assert plan.parameter[-1] == 5


def test_build_safe_sql_does_not_misread_internal_as_intern():
    plan = validate_sql_plan(build_safe_sql('tampilkan lowongan internal audit di jakarta', limit=5))
    assert not any(param == 'intern' for param in plan.parameter)
    assert '%jakarta%' in plan.parameter
