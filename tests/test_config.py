from hwlogger.services.config_service import AppConfig, ConfigService
from hwlogger.services.sensor_manager import SensorManager


def test_config_roundtrip(tmp_path):
    service = ConfigService(tmp_path / "config.json")
    config = AppConfig(log_directory="/tmp/example", decimals=3)
    service.save(config)
    assert service.load() == config
    assert not list(tmp_path.glob(".config.json.*"))


def test_corrupt_config_is_backed_up(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{broken", encoding="utf-8")
    service = ConfigService(path)
    assert service.load() == AppConfig()
    assert service.warning
    assert list(tmp_path.glob("config.json.corrupt-*"))


def test_custom_sensor_name_has_priority(monkeypatch):
    monkeypatch.setenv("HWLOGGER_FAKE_SENSORS", "1")
    manager = SensorManager(
        AppConfig(custom_names={"fake:temperature": "Моё имя датчика"})
    )
    sensors = {sensor.sensor_id: sensor for sensor in manager.scan()}
    assert sensors["fake:temperature"].name == "Моё имя датчика"
