import health_poller


def test_build_point_shape():
    point = health_poller.build_point("DEVICE", "site-a", 1, 12.3)
    # InfluxDB Point exposes dict-like access via to_line_protocol
    lp = point.to_line_protocol()
    assert lp.startswith("device_health,device_name=DEVICE,site=site-a")
    assert "latency=12.3" in lp
    assert "status=1i" in lp
