from smartjobs.qdrant_store import make_qdrant_point_id


def test_make_qdrant_point_id_is_uuid_and_deterministic():
    value1 = make_qdrant_point_id("1fcc63fca83e2912fd9902b6ea0330e571f00daf", 0)
    value2 = make_qdrant_point_id("1fcc63fca83e2912fd9902b6ea0330e571f00daf", 0)
    value3 = make_qdrant_point_id("1fcc63fca83e2912fd9902b6ea0330e571f00daf", 1)

    assert value1 == value2
    assert value1 != value3
    assert len(value1) == 36
    assert value1.count("-") == 4
