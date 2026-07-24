from hwlogger.models.sensor_statistics import OnlineStatistics


def test_online_statistics_zero_and_none():
    stats = OnlineStatistics()
    stats.add(None)
    stats.add(0)
    stats.add(10)
    assert stats.count == 2
    assert stats.minimum == 0
    assert stats.average == 5
    assert stats.maximum == 10
