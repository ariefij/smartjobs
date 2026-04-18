from smartjobs.normalizers import infer_seniority, split_location, standardize_job_title, standardize_work_type


def test_standardize_job_title_basic():
    assert standardize_job_title("data analyst") == "Data Analyst"


def test_standardize_work_type_indonesian():
    assert standardize_work_type("Paruh waktu") == "Part-time"


def test_split_location_city_province():
    city, province = split_location("Jakarta Selatan, Jakarta Raya")
    assert city == "Jakarta Selatan"
    assert province == "Jakarta Raya"


def test_infer_seniority_does_not_match_internal_as_intern():
    assert infer_seniority("Senior Data Scientist", "Bekerja di tim internal platform data") == "Senior"
