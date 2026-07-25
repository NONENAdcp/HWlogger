from __future__ import annotations

from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QMessageBox, QSystemTrayIcon

from hwlogger.services.config_service import AppConfig, ConfigService
from hwlogger.ui.main_window import MainWindow


def _window(tmp_path, monkeypatch, qtbot, *, tray_available=True, close_to_tray=True):
    monkeypatch.setenv("HWLOGGER_FAKE_SENSORS", "1")
    config = AppConfig(
        log_directory=str(tmp_path / "logs"),
        ui_interval_ms=50,
        close_to_tray=close_to_tray,
    )
    window = MainWindow(
        ConfigService(tmp_path / "config.json"),
        config,
        tray_available=tray_available,
    )
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: bool(window.latest_values), timeout=2000)
    return window


def _exit(window):
    window.request_exit()
    assert window._shutdown_complete
    assert not window.polling.thread.isRunning()


def test_available_tray_creates_icon_and_unavailable_tray_is_safe(
    tmp_path, monkeypatch, qtbot
):
    available = _window(tmp_path / "available", monkeypatch, qtbot)
    assert available.tray_controller is not None
    assert isinstance(available.tray_controller.tray, QSystemTrayIcon)
    _exit(available)

    unavailable = _window(
        tmp_path / "unavailable",
        monkeypatch,
        qtbot,
        tray_available=False,
    )
    assert unavailable.tray_controller is None
    assert not unavailable.settings_tab.close_to_tray.isEnabled()
    unavailable.close()
    assert unavailable._shutdown_complete


def test_close_hides_with_tray_but_full_closes_when_disabled(
    tmp_path, monkeypatch, qtbot
):
    hidden = _window(tmp_path / "hidden", monkeypatch, qtbot)
    hidden.close()
    assert hidden.isHidden()
    assert hidden.polling.thread.isRunning()
    assert not hidden._shutdown_complete
    _exit(hidden)

    closed = _window(
        tmp_path / "closed",
        monkeypatch,
        qtbot,
        close_to_tray=False,
    )
    closed.close()
    assert closed._shutdown_complete
    assert not closed.polling.thread.isRunning()


def test_tray_show_and_hide_actions_control_window(tmp_path, monkeypatch, qtbot):
    window = _window(tmp_path, monkeypatch, qtbot)
    controller = window.tray_controller
    assert controller is not None
    raised = Mock()
    activated = Mock()
    monkeypatch.setattr(window, "raise_", raised)
    monkeypatch.setattr(window, "activateWindow", activated)

    controller.hide_action.trigger()
    assert window.isHidden()
    controller.show_action.trigger()
    assert window.isVisible()
    raised.assert_called_once()
    activated.assert_called_once()
    _exit(window)


def test_tray_activation_reasons_handle_only_double_click(
    tmp_path, monkeypatch, qtbot
):
    window = _window(tmp_path, monkeypatch, qtbot)
    controller = window.tray_controller
    assert controller is not None
    window.hide()
    show = Mock(wraps=controller.show_window)
    monkeypatch.setattr(controller, "show_window", show)

    controller.tray.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
    controller.tray.activated.emit(QSystemTrayIcon.ActivationReason.Context)
    assert show.call_count == 0
    assert window.isHidden()

    controller.tray.activated.emit(QSystemTrayIcon.ActivationReason.DoubleClick)
    assert show.call_count == 1
    assert window.isVisible()
    controller.tray.activated.emit(QSystemTrayIcon.ActivationReason.DoubleClick)
    assert show.call_count == 2
    assert window.isVisible()
    _exit(window)


def test_kde_double_trigger_fallback_shows_window(tmp_path, monkeypatch, qtbot):
    window = _window(tmp_path, monkeypatch, qtbot)
    controller = window.tray_controller
    assert controller is not None
    window.hide()
    controller.tray.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
    assert window.isHidden()
    controller.tray.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
    assert window.isVisible()
    _exit(window)


def test_double_click_restores_raises_and_activates_window(
    tmp_path, monkeypatch, qtbot
):
    window = _window(tmp_path, monkeypatch, qtbot)
    controller = window.tray_controller
    assert controller is not None
    window.showMinimized()
    show_normal = Mock(wraps=window.showNormal)
    raised = Mock()
    activated = Mock()
    monkeypatch.setattr(window, "showNormal", show_normal)
    monkeypatch.setattr(window, "raise_", raised)
    monkeypatch.setattr(window, "activateWindow", activated)

    controller.tray.activated.emit(QSystemTrayIcon.ActivationReason.DoubleClick)
    show_normal.assert_called_once()
    raised.assert_called_once()
    activated.assert_called_once()
    _exit(window)


def test_close_to_tray_keeps_active_recording_running(
    tmp_path, monkeypatch, qtbot
):
    window = _window(tmp_path, monkeypatch, qtbot)
    window.sensors[0].selected_for_log = True
    window.start_recording()
    window.close()
    assert window.isHidden()
    assert window.logger.active
    assert window.log_timer.isActive()
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    _exit(window)


@pytest.mark.parametrize("close_to_tray", [True, False])
def test_tray_exit_always_performs_idempotent_full_shutdown(
    tmp_path, monkeypatch, qtbot, close_to_tray
):
    window = _window(
        tmp_path,
        monkeypatch,
        qtbot,
        close_to_tray=close_to_tray,
    )
    controller = window.tray_controller
    assert controller is not None
    original_stop = window.polling.stop
    stop = Mock(side_effect=original_stop)
    monkeypatch.setattr(window.polling, "stop", stop)

    controller.exit_action.trigger()
    window.request_exit()
    assert window._shutdown_complete
    assert stop.call_count == 1
    assert not controller.tray.isVisible()


def test_active_recording_is_finished_by_tray_exit(tmp_path, monkeypatch, qtbot):
    window = _window(tmp_path, monkeypatch, qtbot)
    window.sensors[0].selected_for_log = True
    window.start_recording()
    window._log_row()
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    window.request_exit()

    assert window._shutdown_complete
    assert not window.logger.active
    assert len(list((tmp_path / "logs").glob("hwlog_*.json"))) == 1
    assert len(list((tmp_path / "logs").glob("hwlog_*_summary.csv"))) == 1


def test_close_notification_is_shown_only_once(tmp_path, monkeypatch, qtbot):
    window = _window(tmp_path, monkeypatch, qtbot)
    controller = window.tray_controller
    assert controller is not None
    show_message = Mock()
    monkeypatch.setattr(controller.tray, "showMessage", show_message)

    window.close()
    controller.show_window()
    window.close()
    assert show_message.call_count == 1
    _exit(window)


def test_close_to_tray_setting_is_saved_and_restored(tmp_path, monkeypatch, qtbot):
    path = tmp_path / "config.json"
    monkeypatch.setenv("HWLOGGER_FAKE_SENSORS", "1")
    service = ConfigService(path)
    window = MainWindow(
        service,
        AppConfig(log_directory=str(tmp_path / "logs"), close_to_tray=True),
        tray_available=True,
    )
    qtbot.addWidget(window)
    window.settings_tab.close_to_tray.setChecked(False)
    window.save_settings()
    assert not service.load().close_to_tray
    window.request_exit()


def test_system_tray_availability_check_is_used(tmp_path, monkeypatch, qtbot):
    monkeypatch.setenv("HWLOGGER_FAKE_SENSORS", "1")
    monkeypatch.setattr(
        QSystemTrayIcon,
        "isSystemTrayAvailable",
        staticmethod(lambda: False),
    )
    window = MainWindow(
        ConfigService(tmp_path / "config.json"),
        AppConfig(log_directory=str(tmp_path / "logs")),
    )
    qtbot.addWidget(window)
    window.show()
    assert window.tray_controller is None
    window.close()
    assert window._shutdown_complete
