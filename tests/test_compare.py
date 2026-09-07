from saccloud.compare import compare_rows


def test_tolerance_accepts_small_float_difference():
    t = {"abs": 1e-12, "rel": 1e-9}
    r = compare_rows([{"value":"0.470588235294117647"}], [{"value":"0.4705882352941176"}], t)
    assert r["verdict"] == "CONFORM"


def test_value_divergence_is_detected():
    t = {"abs": 1e-12, "rel": 1e-9}
    r = compare_rows([{"value":"0.64"}], [{"value":"0.60"}], t)
    assert r["verdict"] == "DIVERGENT"
